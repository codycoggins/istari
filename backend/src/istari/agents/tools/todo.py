"""TODO agent tools — create, list, update, and prioritize TODOs."""

import contextlib
import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from istari.llm.router import completion
from istari.models.todo import Todo, TodoStatus
from istari.tools.todo.manager import TodoManager

from .base import AgentContext, AgentTool, normalize_status

logger = logging.getLogger(__name__)

_QUADRANT_LABELS: dict[tuple[bool | None, bool | None], str] = {
    (True, True): "Q1 — Do Now",
    (False, True): "Q2 — Schedule",
    (None, True): "Q2 — Schedule",
    (True, False): "Q3 — Contain",
    (True, None): "Q3 — Contain",
    (False, False): "Q4 — Drop",
}

_CLASSIFY_SYSTEM_PROMPT = """\
You classify TODO items using the Eisenhower matrix.

For each title return a JSON object with:
- "title": the original title (unchanged)
- "urgent": true if time-sensitive or immediately impactful, false if not, null if unclear
- "important": true if significant to goals/values/outcomes, false if not, null if unclear
- "uncertain": true if you genuinely cannot tell from the title alone

Return a JSON array — one object per title, in order. No prose, no markdown fences.

Example input: ["Call dentist", "Reorganize bookshelf", "Fix prod outage"]
Example output:
[
  {"title": "Call dentist", "urgent": false, "important": true, "uncertain": false},
  {"title": "Reorganize bookshelf", "urgent": false, "important": false, "uncertain": false},
  {"title": "Fix prod outage", "urgent": true, "important": true, "uncertain": false}
]"""


async def _classify_titles(titles: list[str]) -> list[dict[str, Any]]:
    """Call LLM to classify titles; returns empty list on any error."""
    try:
        resp = await completion(
            "todo_classification",
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(titles)},
            ],
        )
        raw = resp.choices[0].message.content or ""
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        logger.debug("TODO classification failed", exc_info=True)
    return []


def make_todo_tools(session: AsyncSession, context: AgentContext) -> list[AgentTool]:
    """Return TODO tools bound to the given session and context."""

    async def list_todos(filter: str = "open") -> str:
        mgr = TodoManager(session)
        if filter == "all":
            todos = await mgr.list_visible()
        elif filter == "complete":
            stmt = (
                select(Todo)
                .where(Todo.status == TodoStatus.COMPLETE)
                .order_by(Todo.updated_at.desc())
            )
            result = await session.execute(stmt)
            todos = list(result.scalars().all())
        else:
            todos = await mgr.list_open()

        if not todos:
            return "No TODOs found."
        lines = []
        for t in todos:
            status_tag = f" [{t.status.value}]" if t.status != TodoStatus.OPEN else ""
            quadrant = _QUADRANT_LABELS.get((t.urgent, t.important), "")
            quad_tag = f" ({quadrant})" if quadrant else ""
            lines.append(f"- (id={t.id}) {t.title}{status_tag}{quad_tag}")
        return "\n".join(lines)

    async def create_todos(titles: list[str]) -> str:
        mgr = TodoManager(session)
        created: list[Todo] = []
        for title in titles:
            todo = await mgr.create(title=title.strip(), source="chat")
            created.append(todo)
        await session.commit()
        context.todo_created = True

        # Auto-classify in the background — update DB but don't block the response
        classifications = await _classify_titles([t.title for t in created])
        uncertain_titles: list[str] = []
        for todo, cls in zip(created, classifications, strict=False):
            urgent = cls.get("urgent")
            important = cls.get("important")
            uncertain = cls.get("uncertain", False)
            if uncertain:
                uncertain_titles.append(todo.title)
            await mgr.set_urgency_importance(todo.id, urgent, important)
        if classifications:
            await session.commit()

        titles_str = ", ".join(f'"{t.title}"' for t in created)
        summary = (
            f'Added {len(created)} TODOs: {titles_str}'
            if len(created) > 1
            else f'Added TODO: "{created[0].title}"'
        )
        if uncertain_titles:
            listed = ", ".join(f'"{t}"' for t in uncertain_titles)
            summary += (
                f"\n\nI wasn't sure how to classify: {listed}. "
                "Are these urgent, important, both, or neither?"
            )
        return summary

    async def update_todo_status(query: str, status: str) -> str:
        normalized = normalize_status(status)
        try:
            new_status = TodoStatus(normalized)
        except ValueError:
            valid = ", ".join(s.value for s in TodoStatus)
            return f'"{status}" is not a valid status. Valid values: {valid}.'

        mgr = TodoManager(session)

        # Try numeric ID first
        with contextlib.suppress(ValueError, TypeError):
            todo_id = int(query)
            todo = await mgr.get(todo_id)
            if todo is not None:
                await mgr.set_status(todo.id, new_status)
                await session.commit()
                context.todo_updated = True
                return f'Updated "{todo.title}" to {new_status.value}.'

        # Pattern match — update ALL matching todos
        stmt = select(Todo).where(Todo.title.ilike(f"%{query}%"))
        result = await session.execute(stmt)
        todos = list(result.scalars().all())

        if not todos:
            return f'No TODOs found matching "{query}".'

        for todo in todos:
            await mgr.set_status(todo.id, new_status)
        await session.commit()
        context.todo_updated = True

        if len(todos) == 1:
            return f'Updated "{todos[0].title}" to {new_status.value}.'
        titles_list = [f'"{t.title}"' for t in todos]
        return f"Updated {len(todos)} TODOs to {new_status.value}: " + ", ".join(titles_list)

    async def update_todo_priority(query: str, urgent: bool | None, important: bool | None) -> str:
        """Find a TODO and set its Eisenhower urgency/importance."""
        mgr = TodoManager(session)

        # Try numeric ID first
        with contextlib.suppress(ValueError, TypeError):
            todo_id = int(query)
            todo = await mgr.get(todo_id)
            if todo is not None:
                await mgr.set_urgency_importance(todo.id, urgent, important)
                await session.commit()
                context.todo_updated = True
                quadrant = _QUADRANT_LABELS.get((urgent, important), "unclassified")
                return f'Updated "{todo.title}" → {quadrant}.'

        # Pattern match
        stmt = select(Todo).where(Todo.title.ilike(f"%{query}%"))
        result = await session.execute(stmt)
        todos = list(result.scalars().all())

        if not todos:
            return f'No TODOs found matching "{query}".'

        for todo in todos:
            await mgr.set_urgency_importance(todo.id, urgent, important)
        await session.commit()
        context.todo_updated = True
        quadrant = _QUADRANT_LABELS.get((urgent, important), "unclassified")

        if len(todos) == 1:
            return f'Updated "{todos[0].title}" → {quadrant}.'
        titles_list = [f'"{t.title}"' for t in todos]
        return f"Updated {len(todos)} TODOs to {quadrant}: " + ", ".join(titles_list)

    async def set_today_focus(query: str, focus: bool) -> str:
        mgr = TodoManager(session)

        # Soft cap: warn when already at 5 tasks focused for today
        if focus:
            current = await mgr.list_today()
            if len(current) >= 5:
                titles = ", ".join(f'"{t.title}"' for t in current)
                return (
                    f"You already have 5 tasks focused for today: {titles}. "
                    "Consider removing one before adding another."
                )

        # Try numeric ID first
        with contextlib.suppress(ValueError, TypeError):
            todo_id = int(query)
            todo = await mgr.get(todo_id)
            if todo is not None:
                await mgr.set_today(todo.id, focus)
                await session.commit()
                context.todo_updated = True
                action = "Added" if focus else "Removed"
                prep = "to" if focus else "from"
                return f'{action} "{todo.title}" {prep} today\'s focus.'

        # Pattern match
        stmt = select(Todo).where(Todo.title.ilike(f"%{query}%"))
        result = await session.execute(stmt)
        todos = list(result.scalars().all())

        if not todos:
            return f'No TODOs found matching "{query}".'

        updated: list[Todo] = []
        for todo in todos:
            await mgr.set_today(todo.id, focus)
            updated.append(todo)
        await session.commit()
        context.todo_updated = True
        action = "Added" if focus else "Removed"
        prep = "to" if focus else "from"
        if len(updated) == 1:
            return f'{action} "{updated[0].title}" {prep} today\'s focus.'
        titles_list = [f'"{t.title}"' for t in updated]
        return f"{action} {len(updated)} tasks {prep} today's focus: " + ", ".join(titles_list)

    async def get_today_focus() -> str:
        mgr = TodoManager(session)
        todos = await mgr.list_today()
        if not todos:
            return "You haven't set any tasks to focus on today."
        lines = [f"Today's focus ({len(todos)}/5):"]
        for t in todos:
            quadrant = _QUADRANT_LABELS.get((t.urgent, t.important), "")
            quad_tag = f" [{quadrant}]" if quadrant else ""
            lines.append(f"- (id={t.id}) {t.title}{quad_tag}")
        return "\n".join(lines)

    async def get_priorities() -> str:
        mgr = TodoManager(session)
        today_todos = await mgr.list_today()
        selected = today_todos[:3]
        if len(selected) < 3:
            exclude = [t.id for t in selected]
            needed = 3 - len(selected)
            extra = await mgr.get_prioritized(limit=needed, exclude_ids=exclude)
            selected = selected + extra
        if not selected:
            return "No active TODOs right now."
        lines = ["Here's what I'd focus on:"]
        today_ids = {t.id for t in today_todos}
        for i, t in enumerate(selected, 1):
            quadrant = _QUADRANT_LABELS.get((t.urgent, t.important), "")
            quad_tag = f" [{quadrant}]" if quadrant else ""
            priority_tag = f" (priority {t.priority})" if t.priority is not None else ""
            today_tag = " ★ Today" if t.id in today_ids else ""
            lines.append(f"{i}. {t.title}{quad_tag}{priority_tag}{today_tag}")
        return "\n".join(lines)

    return [
        AgentTool(
            name="list_todos",
            description=(
                "List the user's TODOs. Use filter='open' for active tasks (default), "
                "'all' for everything including completed, 'complete' for done items."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "enum": ["open", "all", "complete"],
                        "description": "Which TODOs to return.",
                    }
                },
                "required": [],
            },
            fn=list_todos,
        ),
        AgentTool(
            name="create_todos",
            description=(
                "Create one or more TODO items. Pass a list of task titles — even for a "
                "single task, wrap it in a list. Use concise action phrases starting with "
                "a verb (e.g., 'Buy groceries', 'Call dentist'). After creation, "
                "urgency/importance are auto-classified; if uncertain, ask the user."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "titles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of TODO titles to create.",
                    }
                },
                "required": ["titles"],
            },
            fn=create_todos,
        ),
        AgentTool(
            name="update_todo_status",
            description=(
                "Update the status of one or more TODOs. 'query' should be the task title "
                "keywords (not 'todos' or 'tasks') or a numeric ID. If multiple TODOs match, "
                "all are updated. Valid statuses: open, in_progress, blocked, complete, deferred."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Task title keywords or numeric ID.",
                    },
                    "status": {
                        "type": "string",
                        "description": "New status for the TODO.",
                    },
                },
                "required": ["query", "status"],
            },
            fn=update_todo_status,
        ),
        AgentTool(
            name="update_todo_priority",
            description=(
                "Set the Eisenhower urgency/importance on a TODO. Use this when the user "
                "clarifies whether a task is urgent and/or important. 'query' is the task "
                "title keywords or numeric ID. Pass null for fields that remain unknown."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Task title keywords or numeric ID.",
                    },
                    "urgent": {
                        "type": ["boolean", "null"],
                        "description": "True if time-sensitive, false if not, null if unknown.",
                    },
                    "important": {
                        "type": ["boolean", "null"],
                        "description": "True if high-impact, false if not, null if unknown.",
                    },
                },
                "required": ["query", "urgent", "important"],
            },
            fn=update_todo_priority,
        ),
        AgentTool(
            name="get_priorities",
            description=(
                "Return the top 3 highest-priority active TODOs, sorted by Eisenhower "
                "quadrant (Q1 first) then explicit priority, due date, and recency."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            fn=get_priorities,
        ),
        AgentTool(
            name="set_today_focus",
            description=(
                "Mark a TODO as today's focus (or remove it). Use this when the user "
                "says they want to work on something today or focus on it. Soft limit: 5."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Task title keywords or numeric ID.",
                    },
                    "focus": {
                        "type": "boolean",
                        "description": "True to add to today's focus, false to remove.",
                    },
                },
                "required": ["query", "focus"],
            },
            fn=set_today_focus,
        ),
        AgentTool(
            name="get_today_focus",
            description="List the tasks the user has focused on for today.",
            parameters={"type": "object", "properties": {}, "required": []},
            fn=get_today_focus,
        ),
    ]
