"""Tests for the Todoist migration — pure mappers + orchestration with a fake client."""

import datetime

import httpx
import pytest

from istari.models.project import Project, ProjectStatus
from istari.models.todo import PrioritySource, Todo, TodoStatus
from istari.tools.todoist.client import (
    TodoistClient,
    TodoistError,
    TodoistProjectLimitError,
)
from istari.tools.todoist.migrate import (
    build_plan,
    format_task,
    map_priority,
    project_comment,
    run_migration,
    sanitize_label,
)

UTC = datetime.UTC


# ── Real client against a mock transport (v1 wire contract) ───────────────────


def _client_with(handler) -> TodoistClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(
        transport=transport,
        base_url="https://api.todoist.com/api/v1",
        headers={"Authorization": "Bearer test"},
    )
    return TodoistClient("test", client=http)


class TestTodoistClient:
    async def test_list_projects_unwraps_and_paginates(self):
        def handler(request: httpx.Request) -> httpx.Response:
            cursor = request.url.params.get("cursor")
            if cursor is None:
                return httpx.Response(
                    200, json={"results": [{"id": "1", "name": "A"}], "next_cursor": "c2"}
                )
            return httpx.Response(
                200, json={"results": [{"id": "2", "name": "B"}], "next_cursor": None}
            )

        client = _client_with(handler)
        projects = await client.list_projects()
        assert [p["name"] for p in projects] == ["A", "B"]

    async def test_create_project_limit_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="project limit reached")

        client = _client_with(handler)
        with pytest.raises(TodoistProjectLimitError):
            await client.create_project("New")

    async def test_non_success_raises_todoist_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        client = _client_with(handler)
        with pytest.raises(TodoistError):
            await client.list_tasks("1")


# ── Fake client ───────────────────────────────────────────────────────────────


class FakeClient:
    """In-memory stand-in for TodoistClient. Raises the limit error after `limit`."""

    def __init__(
        self,
        existing_projects: list[dict] | None = None,
        *,
        limit: int | None = None,
        tasks_by_project: dict[str, list[dict]] | None = None,
    ) -> None:
        self.projects = list(existing_projects or [{"id": "personal-1", "name": "Personal"}])
        self.limit = limit
        self.tasks_by_project = tasks_by_project or {}
        self.created_projects: list[str] = []
        self.created_tasks: list[dict] = []
        self.created_comments: list[tuple[str, str]] = []

    async def list_projects(self) -> list[dict]:
        return list(self.projects)

    async def create_project(self, name: str) -> dict:
        if self.limit is not None and len(self.projects) >= self.limit:
            raise TodoistProjectLimitError(name)
        proj = {"id": f"p{len(self.projects) + 1}", "name": name}
        self.projects.append(proj)
        self.created_projects.append(name)
        return proj

    async def list_tasks(self, project_id: str) -> list[dict]:
        return list(self.tasks_by_project.get(project_id, []))

    async def create_task(self, **fields: object) -> dict:
        self.created_tasks.append(fields)
        pid = fields["project_id"]
        self.tasks_by_project.setdefault(pid, []).append({"content": fields["content"]})
        return {"id": f"t{len(self.created_tasks)}", **fields}

    async def create_comment(self, project_id: str, content: str) -> dict:
        self.created_comments.append((project_id, content))
        return {"id": "c1"}


# ── DB helpers ────────────────────────────────────────────────────────────────


async def _make_project(session, name, status=ProjectStatus.active, **kw):
    project = Project(name=name, status=status, **kw)
    session.add(project)
    await session.flush()
    return project


async def _make_todo(session, title, project_id, status=TodoStatus.OPEN, **kw):
    todo = Todo(title=title, status=status, project_id=project_id, **kw)
    session.add(todo)
    await session.flush()
    return todo


# ── Pure mappers ──────────────────────────────────────────────────────────────


class TestMapPriority:
    @pytest.mark.parametrize(
        ("urgent", "important", "expected"),
        [
            (True, True, 4),
            (True, False, 3),
            (False, True, 2),
            (False, False, 1),
            (None, None, 1),
        ],
    )
    def test_quadrants(self, urgent, important, expected):
        assert map_priority(urgent, important) == expected


class TestSanitizeLabel:
    def test_spaces_become_underscores(self):
        assert sanitize_label("Home Renovation") == "Home_Renovation"


class TestFormatTask:
    def test_content_and_priority(self):
        todo = Todo(
            id=1,
            title="Call plumber",
            status=TodoStatus.OPEN,
            urgent=True,
            important=True,
        )
        project = Project(name="House")
        payload = format_task(todo, project, is_overflow=False)
        assert payload["content"] == "Call plumber"
        assert payload["priority"] == 4

    def test_metadata_block_holds_non_native_fields(self):
        todo = Todo(
            id=7,
            title="Draft doc",
            body="the body text",
            status=TodoStatus.BLOCKED,
            priority=2,
            priority_source=PrioritySource.USER_SET,
            source="gmail",
            source_link="https://mail.example/1",
            tags=["work", "q3"],
        )
        project = Project(name="Planning")
        desc = format_task(todo, project, is_overflow=False)["description"]
        assert desc.startswith("the body text")
        assert "— Istari metadata —" in desc
        assert "Status: blocked" in desc
        assert "Priority: 2 (user_set)" in desc
        assert "Source: gmail" in desc
        assert "Tags: work, q3" in desc
        assert "Istari todo ID: 7" in desc

    def test_tags_become_sanitized_labels(self):
        todo = Todo(id=1, title="x", status=TodoStatus.OPEN, tags=["deep work", "focus"])
        payload = format_task(todo, Project(name="P"), is_overflow=False)
        assert payload["labels"] == ["deep_work", "focus"]

    def test_all_day_due_is_date_only(self):
        todo = Todo(
            id=1,
            title="x",
            status=TodoStatus.OPEN,
            due_date=datetime.datetime(2026, 7, 10, tzinfo=UTC),
        )
        payload = format_task(todo, Project(name="P"), is_overflow=False)
        assert payload["due_date"] == "2026-07-10"
        assert "due_datetime" not in payload

    def test_timed_due_is_datetime(self):
        todo = Todo(
            id=1,
            title="x",
            status=TodoStatus.OPEN,
            due_date=datetime.datetime(2026, 7, 10, 14, 30, tzinfo=UTC),
        )
        payload = format_task(todo, Project(name="P"), is_overflow=False)
        assert payload["due_datetime"].startswith("2026-07-10T14:30")
        assert "due_date" not in payload

    def test_overflow_adds_project_label_and_context(self):
        todo = Todo(id=1, title="x", status=TodoStatus.OPEN, tags=["a"])
        project = Project(name="Side Quest", goal="ship it", description="notes here")
        payload = format_task(todo, project, is_overflow=True)
        assert "Side_Quest" in payload["labels"]
        assert "Project: Side Quest" in payload["description"]
        assert "Project goal: ship it" in payload["description"]
        assert "Project notes: notes here" in payload["description"]


class TestProjectComment:
    def test_includes_goal_and_notes(self):
        project = Project(
            id=3,
            name="Alpha",
            status=ProjectStatus.active,
            goal="win",
            description="the notes",
        )
        comment = project_comment(project)
        assert "Imported from Istari" in comment
        assert "Goal: win" in comment
        assert "Notes: the notes" in comment
        assert "Istari project ID: 3" in comment


class TestBuildPlan:
    def test_orders_most_tasks_first(self):
        small = Project(name="Small", status=ProjectStatus.active)
        small.todos = [Todo(id=1, title="a", status=TodoStatus.OPEN)]
        big = Project(name="Big", status=ProjectStatus.active)
        big.todos = [
            Todo(id=2, title="b", status=TodoStatus.OPEN),
            Todo(id=3, title="c", status=TodoStatus.IN_PROGRESS),
        ]
        plans = build_plan([small, big])
        assert [p.project.name for p in plans] == ["Big", "Small"]

    def test_excludes_projects_with_no_actionable_todos(self):
        project = Project(name="Done", status=ProjectStatus.active)
        project.todos = [
            Todo(id=1, title="a", status=TodoStatus.COMPLETE),
            Todo(id=2, title="b", status=TodoStatus.DEFERRED),
        ]
        assert build_plan([project]) == []

    def test_excludes_non_active_projects(self):
        project = Project(name="Paused", status=ProjectStatus.paused)
        project.todos = [Todo(id=1, title="a", status=TodoStatus.OPEN)]
        assert build_plan([project]) == []

    def test_actionable_filter_drops_complete_and_deferred(self):
        project = Project(name="Mixed", status=ProjectStatus.active)
        project.todos = [
            Todo(id=1, title="keep", status=TodoStatus.OPEN),
            Todo(id=2, title="drop-complete", status=TodoStatus.COMPLETE),
            Todo(id=3, title="drop-deferred", status=TodoStatus.DEFERRED),
        ]
        plans = build_plan([project])
        assert [t.title for t in plans[0].todos] == ["keep"]


# ── Orchestration ─────────────────────────────────────────────────────────────


class TestRunMigration:
    async def test_creates_projects_and_tasks(self, db_session):
        p1 = await _make_project(db_session, "Alpha")
        await _make_todo(db_session, "a1", p1.id)
        p2 = await _make_project(db_session, "Beta")
        await _make_todo(db_session, "b1", p2.id)
        await _make_todo(db_session, "b2", p2.id)

        client = FakeClient()
        summary = await run_migration(db_session, client)

        # Beta has more tasks → created first.
        assert client.created_projects == ["Beta", "Alpha"]
        assert summary.tasks_created == 3
        assert len(client.created_comments) == 2  # one per created project

    async def test_no_personal_project_raises(self, db_session):
        p1 = await _make_project(db_session, "Alpha")
        await _make_todo(db_session, "a1", p1.id)
        client = FakeClient(existing_projects=[{"id": "inbox", "name": "Inbox"}])
        with pytest.raises(Exception, match="personal"):
            await run_migration(db_session, client)

    async def test_project_limit_overflows_to_personal(self, db_session):
        big = await _make_project(db_session, "Big")
        await _make_todo(db_session, "big1", big.id)
        await _make_todo(db_session, "big2", big.id)
        small = await _make_project(db_session, "Small")
        await _make_todo(db_session, "small1", small.id)

        # Personal already occupies a slot; limit=2 allows exactly one new project.
        client = FakeClient(limit=2)
        summary = await run_migration(db_session, client)

        assert summary.projects_created == ["Big"]
        assert summary.projects_overflowed == ["Small"]
        overflow_tasks = [t for t in client.created_tasks if t["project_id"] == "personal-1"]
        assert len(overflow_tasks) == 1
        assert "Small" in overflow_tasks[0]["labels"]

    async def test_idempotent_rerun_skips_existing(self, db_session):
        p1 = await _make_project(db_session, "Alpha")
        await _make_todo(db_session, "a1", p1.id)

        client = FakeClient(
            existing_projects=[
                {"id": "personal-1", "name": "Personal"},
                {"id": "pA", "name": "Alpha"},
            ],
            tasks_by_project={"pA": [{"content": "a1"}]},
        )
        summary = await run_migration(db_session, client)

        assert client.created_projects == []
        assert client.created_tasks == []
        assert summary.projects_reused == ["Alpha"]
        assert summary.tasks_skipped == 1
        assert summary.tasks_created == 0

    async def test_dry_run_makes_no_writes(self, db_session):
        p1 = await _make_project(db_session, "Alpha")
        await _make_todo(db_session, "a1", p1.id)

        client = FakeClient()
        summary = await run_migration(db_session, client, dry_run=True)

        assert client.created_projects == []
        assert client.created_tasks == []
        assert client.created_comments == []
        assert summary.dry_run is True
        assert summary.tasks_created == 1
        assert "DRY RUN" in summary.render()
