"""TODO agent tools — create, list, update, and prioritize TODOs."""

import contextlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from istari.models.todo import Todo, TodoStatus
from istari.tools.todo.manager import TodoManager

from .base import AgentContext, AgentTool, normalize_status


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
            lines.append(f"- (id={t.id}) {t.title}{status_tag}")
        return "\n".join(lines)

    async def create_todos(titles: list[str]) -> str:
        mgr = TodoManager(session)
        created = []
        for title in titles:
            todo = await mgr.create(title=title.strip(), source="chat")
            created.append(todo.title)
        await session.commit()
        context.todo_created = True
        if len(created) == 1:
            return f'Added TODO: "{created[0]}"'
        return f"Added {len(created)} TODOs: " + ", ".join(f'"{t}"' for t in created)

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
        titles = [f'"{t.title}"' for t in todos]
        return f"Updated {len(todos)} TODOs to {new_status.value}: " + ", ".join(titles)

    async def get_priorities() -> str:
        mgr = TodoManager(session)
        todos = await mgr.get_prioritized(limit=3)
        if not todos:
            return "No active TODOs right now."
        lines = ["Here's what I'd focus on:"]
        for i, t in enumerate(todos, 1):
            line = f"{i}. {t.title}"
            if t.priority is not None:
                line += f" (priority {t.priority})"
            lines.append(line)
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
                "a verb (e.g., 'Buy groceries', 'Call dentist')."
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
                        # valid: open, in_progress, blocked, complete, deferred
                        "description": "New status for the TODO.",
                    },
                },
                "required": ["query", "status"],
            },
            fn=update_todo_status,
        ),
        AgentTool(
            name="get_priorities",
            description="Return the top 3 highest-priority active TODOs.",
            parameters={"type": "object", "properties": {}, "required": []},
            fn=get_priorities,
        ),
    ]
