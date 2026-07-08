"""Migrate Istari active projects and their actionable todos into Todoist.

Field mapping (Istari → Todoist), designed for **no data loss**: anything
Todoist can't represent natively is appended as text — to task descriptions and
to a per-project comment.

    todo.title            → task content
    todo.body + metadata  → task description
    todo.due_date         → due_date / due_datetime
    urgent + important    → task priority (1..4)
    todo.tags             → task labels (+ non-native fields kept in description)
    project.goal/desc     → project comment

Projects are created most-tasks-first. When the account's project limit is hit
(a 403 on create), the remaining projects' tasks overflow into the pre-existing
``#personal`` project, tagged with a label carrying the original project name.
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from istari.models.project import Project, ProjectStatus
from istari.models.todo import Todo, TodoStatus
from istari.tools.project.manager import ProjectManager
from istari.tools.todoist.client import (
    TodoistClient,
    TodoistError,
    TodoistProjectLimitError,
)

logger = logging.getLogger(__name__)

_ACTIONABLE = (TodoStatus.OPEN, TodoStatus.IN_PROGRESS, TodoStatus.BLOCKED)
_METADATA_HEADER = "— Istari metadata —"


# ── Pure mapping helpers ──────────────────────────────────────────────────────


def sanitize_label(name: str) -> str:
    """Todoist labels can't contain whitespace — collapse it to underscores."""
    return "_".join(name.split())


def map_priority(urgent: bool | None, important: bool | None) -> int:
    """Map the Eisenhower flags to Todoist priority (1 default … 4 highest)."""
    if urgent and important:
        return 4
    if urgent:
        return 3
    if important:
        return 2
    return 1


def _due_fields(due: datetime.datetime) -> dict[str, str]:
    """All-day (midnight) → date-only; otherwise a timed RFC3339 due_datetime."""
    due_utc = (
        due.astimezone(datetime.UTC)
        if due.tzinfo is not None
        else due.replace(tzinfo=datetime.UTC)
    )
    if (due_utc.hour, due_utc.minute, due_utc.second) == (0, 0, 0):
        return {"due_date": due_utc.date().isoformat()}
    return {"due_datetime": due_utc.isoformat()}


def _description(todo: Todo, project: Project, *, is_overflow: bool) -> str:
    """Task body followed by an Istari-metadata block of non-native fields."""
    meta: list[str] = []

    def add(label: str, value: object) -> None:
        if value not in (None, "", []):
            meta.append(f"{label}: {value}")

    add("Status", todo.status.value)
    if todo.urgent is not None:
        add("Urgent", "yes" if todo.urgent else "no")
    if todo.important is not None:
        add("Important", "yes" if todo.important else "no")
    if todo.priority is not None:
        src = f" ({todo.priority_source.value})" if todo.priority_source else ""
        add("Priority", f"{todo.priority}{src}")
    add("Tags", ", ".join(todo.tags) if todo.tags else None)
    add("Source", todo.source)
    add("Source link", todo.source_link)
    add("Recurrence", todo.recurrence_rule)
    add("Focused for", todo.today_date.isoformat() if todo.today_date else None)
    add("Created", todo.created_at.isoformat() if todo.created_at else None)
    add("Istari todo ID", todo.id)
    if is_overflow:
        # No dedicated Todoist project, so carry project context on the task.
        add("Project", project.name)
        add("Project goal", project.goal)
        add("Project notes", project.description)

    lines: list[str] = []
    body = (todo.body or "").strip()
    if body:
        lines.append(body)
    if meta:
        if lines:
            lines.append("")
        lines.append(_METADATA_HEADER)
        lines.extend(meta)
    return "\n".join(lines)


def format_task(todo: Todo, project: Project, *, is_overflow: bool) -> dict[str, Any]:
    """Build a Todoist task payload (without ``project_id`` — caller sets it)."""
    payload: dict[str, Any] = {
        "content": todo.title,
        "priority": map_priority(todo.urgent, todo.important),
    }

    description = _description(todo, project, is_overflow=is_overflow)
    if description:
        payload["description"] = description

    if todo.due_date is not None:
        payload.update(_due_fields(todo.due_date))

    labels = list(todo.tags or [])
    if is_overflow:
        labels.append(project.name)
    labels = [sanitize_label(label) for label in labels]
    if labels:
        payload["labels"] = labels

    return payload


def project_comment(project: Project) -> str:
    """Provenance comment carrying project fields Todoist can't store natively."""
    lines: list[str] = []

    def add(label: str, value: object) -> None:
        if value not in (None, "", []):
            lines.append(f"{label}: {value}")

    add("Status", project.status.value)
    add("Goal", project.goal)
    add("Notes", project.description)
    add("Created", project.created_at.isoformat() if project.created_at else None)
    add("Istari project ID", project.id)
    return "Imported from Istari\n" + "\n".join(lines) if lines else ""


@dataclass
class ProjectPlan:
    """A qualifying active project plus the actionable todos to migrate."""

    project: Project
    todos: list[Todo]


def build_plan(projects_with_todos: list[Project]) -> list[ProjectPlan]:
    """Keep active projects with ≥1 actionable todo, ordered most-tasks-first."""
    plans: list[ProjectPlan] = []
    for project in projects_with_todos:
        if project.status != ProjectStatus.active:
            continue
        actionable = [t for t in project.todos if t.status in _ACTIONABLE]
        if actionable:
            plans.append(ProjectPlan(project, actionable))
    plans.sort(key=lambda p: len(p.todos), reverse=True)
    return plans


# ── Orchestration ─────────────────────────────────────────────────────────────


@dataclass
class Summary:
    projects_created: list[str] = field(default_factory=list)
    projects_reused: list[str] = field(default_factory=list)
    projects_overflowed: list[str] = field(default_factory=list)
    tasks_created: int = 0
    tasks_skipped: int = 0
    dry_run: bool = False

    def render(self) -> str:
        mode = "DRY RUN (no writes)" if self.dry_run else "LIVE RUN"
        return (
            f"Todoist migration — {mode}\n"
            f"  Projects created:   {len(self.projects_created)} "
            f"{self.projects_created}\n"
            f"  Projects reused:    {len(self.projects_reused)} "
            f"{self.projects_reused}\n"
            f"  Projects overflowed → #personal: {len(self.projects_overflowed)} "
            f"{self.projects_overflowed}\n"
            f"  Tasks created:      {self.tasks_created}\n"
            f"  Tasks skipped (already present): {self.tasks_skipped}"
        )


def _find_personal(projects: list[dict[str, Any]]) -> dict[str, Any] | None:
    for project in projects:
        if project["name"].casefold() == "personal":
            return project
    for project in projects:
        if "personal" in project["name"].casefold():
            return project
    return None


async def _existing_contents(
    client: TodoistClient, project_id: str, cache: dict[str, set[str]]
) -> set[str]:
    """Set of existing active task contents in a Todoist project (for dedupe)."""
    if project_id not in cache:
        tasks = await client.list_tasks(project_id)
        cache[project_id] = {t["content"] for t in tasks}
    return cache[project_id]


async def _load_project_plans(session: AsyncSession) -> list[ProjectPlan]:
    manager = ProjectManager(session)
    loaded: list[Project] = []
    for project in await manager.list_active():
        with_todos = await manager.get_with_todos(project.id)
        if with_todos is not None:
            loaded.append(with_todos)
    return build_plan(loaded)


async def run_migration(
    session: AsyncSession, client: TodoistClient, *, dry_run: bool = False
) -> Summary:
    """Export active Istari projects/todos to Todoist. Idempotent; dry-run safe."""
    summary = Summary(dry_run=dry_run)
    plans = await _load_project_plans(session)

    existing_projects = await client.list_projects()
    by_name = {p["name"].casefold(): p for p in existing_projects}
    personal = _find_personal(existing_projects)
    if personal is None:
        raise TodoistError(
            "No '#personal' project found in Todoist — overflow tasks have no home. "
            "Create a 'Personal' project first."
        )
    personal_id = personal["id"]

    task_cache: dict[str, set[str]] = {}
    limit_hit = False

    for plan in plans:
        name = plan.project.name
        existing = by_name.get(name.casefold())
        is_overflow = False
        target_id: str | None

        if existing is not None:
            target_id = existing["id"]
            summary.projects_reused.append(name)
        elif limit_hit:
            is_overflow = True
            target_id = personal_id
            summary.projects_overflowed.append(name)
        elif dry_run:
            target_id = None  # would be created live; no id yet
            summary.projects_created.append(name)
        else:
            try:
                created = await client.create_project(name)
            except TodoistProjectLimitError:
                logger.info("Project limit reached; overflowing %r to #personal", name)
                limit_hit = True
                is_overflow = True
                target_id = personal_id
                summary.projects_overflowed.append(name)
            else:
                target_id = created["id"]
                by_name[name.casefold()] = created
                summary.projects_created.append(name)
                comment = project_comment(plan.project)
                if comment:
                    await client.create_comment(target_id, comment)

        contents = (
            await _existing_contents(client, target_id, task_cache)
            if target_id is not None
            else set()
        )

        for todo in plan.todos:
            payload = format_task(todo, plan.project, is_overflow=is_overflow)
            if payload["content"] in contents:
                summary.tasks_skipped += 1
                continue
            contents.add(payload["content"])
            if not dry_run:
                payload["project_id"] = target_id
                await client.create_task(**payload)
            summary.tasks_created += 1

    return summary
