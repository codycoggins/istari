"""Project agent tools — create, list, and manage Projects."""

import contextlib
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from istari.llm.router import completion
from istari.models.project import Project, ProjectStatus
from istari.models.todo import Todo, TodoStatus
from istari.tools.project.manager import ProjectManager
from istari.tools.todo.manager import TodoManager

from .base import AgentContext, AgentTool

logger = logging.getLogger(__name__)


def make_project_tools(session: AsyncSession, context: AgentContext) -> list[AgentTool]:
    """Return project tools bound to the given session and context."""

    async def create_project(name: str, description: str = "", goal: str = "") -> str:
        mgr = ProjectManager(session)
        project = await mgr.create(name=name, description=description, goal=goal)
        await session.commit()
        await session.refresh(project)
        parts = [f'Created project "{project.name}" (id={project.id}).']
        if project.goal:
            parts.append(f"Goal: {project.goal}")
        return " ".join(parts)

    async def list_projects(status: str = "active") -> str:
        mgr = ProjectManager(session)
        if status == "all":
            projects = await mgr.list_all()
        else:
            projects = await mgr.list_active()

        if not projects:
            label = "active" if status != "all" else ""
            return f"No {label} projects found.".strip()

        lines: list[str] = []
        for p in projects:
            # Count associated todos
            stmt = select(Todo).where(
                Todo.project_id == p.id,
                Todo.status.in_((TodoStatus.OPEN, TodoStatus.IN_PROGRESS, TodoStatus.BLOCKED)),
            )
            result = await session.execute(stmt)
            todo_count = len(list(result.scalars().all()))

            next_action_title = "none set"
            if p.next_action_id is not None:
                todo_mgr = TodoManager(session)
                na = await todo_mgr.get(p.next_action_id)
                if na is not None:
                    next_action_title = na.title

            status_tag = f" [{p.status.value}]" if p.status != ProjectStatus.active else ""
            lines.append(
                f"- (id={p.id}) **{p.name}**{status_tag} | "
                f"next: {next_action_title} | {todo_count} open todos"
            )
            if p.goal:
                lines.append(f"  Goal: {p.goal}")

        return "\n".join(lines)

    async def add_todo_to_project(todo_query: str, project_query: str) -> str:
        todo_mgr = TodoManager(session)
        proj_mgr = ProjectManager(session)

        # Resolve todo — numeric ID first
        todo: Todo | None = None
        with contextlib.suppress(ValueError, TypeError):
            todo = await todo_mgr.get(int(todo_query))

        if todo is None:
            stmt = select(Todo).where(Todo.title.ilike(f"%{todo_query}%"))
            result = await session.execute(stmt)
            todos = list(result.scalars().all())
            if not todos:
                return f'No TODOs found matching "{todo_query}".'
            todo = todos[0]

        # Resolve project — numeric ID first
        project: Project | None = None
        with contextlib.suppress(ValueError, TypeError):
            project = await proj_mgr.get(int(project_query))

        if project is None:
            projects = await proj_mgr.get_by_name(project_query)
            if not projects:
                return f'No projects found matching "{project_query}".'
            project = projects[0]

        todo.project_id = project.id
        await session.commit()
        await session.refresh(todo)
        context.todo_updated = True
        return f'Added "{todo.title}" to project "{project.name}".'

    async def set_next_action(project_query: str, todo_query: str) -> str:
        todo_mgr = TodoManager(session)
        proj_mgr = ProjectManager(session)

        # Resolve project
        project: Project | None = None
        with contextlib.suppress(ValueError, TypeError):
            project = await proj_mgr.get(int(project_query))
        if project is None:
            projects = await proj_mgr.get_by_name(project_query)
            if not projects:
                return f'No projects found matching "{project_query}".'
            project = projects[0]

        # Resolve todo
        todo: Todo | None = None
        with contextlib.suppress(ValueError, TypeError):
            todo = await todo_mgr.get(int(todo_query))
        if todo is None:
            stmt = select(Todo).where(Todo.title.ilike(f"%{todo_query}%"))
            result = await session.execute(stmt)
            todos = list(result.scalars().all())
            if not todos:
                return f'No TODOs found matching "{todo_query}".'
            todo = todos[0]

        # Warn if todo doesn't belong to the project
        warning = ""
        if todo.project_id != project.id:
            warning = (
                f' Note: "{todo.title}" is not assigned to this project yet '
                f"(project_id={todo.project_id}). Setting next action anyway."
            )

        await proj_mgr.set_next_action(project.id, todo.id)
        await session.commit()
        await session.refresh(project)
        return f'Set next action for "{project.name}" to "{todo.title}".{warning}'

    async def suggest_next_action(project_query: str) -> str:
        proj_mgr = ProjectManager(session)

        # Resolve project
        project: Project | None = None
        with contextlib.suppress(ValueError, TypeError):
            project = await proj_mgr.get(int(project_query))
        if project is None:
            projects = await proj_mgr.get_by_name(project_query)
            if not projects:
                return f'No projects found matching "{project_query}".'
            project = projects[0]

        # Load todos for this project
        stmt = select(Todo).where(
            Todo.project_id == project.id,
            Todo.status.in_((TodoStatus.OPEN, TodoStatus.IN_PROGRESS, TodoStatus.BLOCKED)),
        )
        result = await session.execute(stmt)
        todos = list(result.scalars().all())

        if not todos:
            return f'No open todos found for project "{project.name}".'

        todo_lines = []
        for t in todos:
            u = "urgent" if t.urgent else ("not-urgent" if t.urgent is False else "?")
            imp = "important" if t.important else ("not-important" if t.important is False else "?")
            todo_lines.append(f"- (id={t.id}) [{t.status.value}] {t.title} [{u}/{imp}]")

        todos_text = "\n".join(todo_lines)
        goal_text = f"Project goal: {project.goal}\n\n" if project.goal else ""

        prompt = (
            f"You are helping prioritize work for the project \"{project.name}\".\n"
            f"{goal_text}"
            f"Open todos:\n{todos_text}\n\n"
            "Which single todo should be the next action? "
            "Consider urgency, importance, and logical sequencing. "
            "Reply with the todo ID and title, then one sentence of reasoning."
        )

        try:
            resp = await completion(
                "chat_response",
                messages=[{"role": "user", "content": prompt}],
            )
            suggestion = resp.choices[0].message.content or "No suggestion available."
        except Exception:
            logger.debug("suggest_next_action LLM call failed", exc_info=True)
            suggestion = "Could not generate a suggestion right now."

        return (
            f'Suggested next action for "{project.name}":\n{suggestion}\n\n'
            "Use set_next_action to confirm this choice."
        )

    return [
        AgentTool(
            name="create_project",
            description="Create a new project with a name, optional description, and goal.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Project name.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of the project.",
                    },
                    "goal": {
                        "type": "string",
                        "description": "The desired outcome or success criteria.",
                    },
                },
                "required": ["name"],
            },
            fn=create_project,
        ),
        AgentTool(
            name="list_projects",
            description=(
                "List projects. status='active' (default) shows active projects; "
                "'all' shows everything including paused and complete."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "all"],
                        "description": "Filter by project status.",
                    }
                },
                "required": [],
            },
            fn=list_projects,
        ),
        AgentTool(
            name="add_todo_to_project",
            description=(
                "Associate a TODO with a project. Use numeric IDs or title/name keywords. "
                "Numeric ID takes precedence over keyword search."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "todo_query": {
                        "type": "string",
                        "description": "TODO ID or title keywords.",
                    },
                    "project_query": {
                        "type": "string",
                        "description": "Project ID or name keywords.",
                    },
                },
                "required": ["todo_query", "project_query"],
            },
            fn=add_todo_to_project,
        ),
        AgentTool(
            name="set_next_action",
            description=(
                "Set the next action todo for a project. Warns if the todo isn't "
                "already assigned to the project."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "project_query": {
                        "type": "string",
                        "description": "Project ID or name keywords.",
                    },
                    "todo_query": {
                        "type": "string",
                        "description": "TODO ID or title keywords.",
                    },
                },
                "required": ["project_query", "todo_query"],
            },
            fn=set_next_action,
        ),
        AgentTool(
            name="suggest_next_action",
            description=(
                "Ask the AI to suggest the best next action for a project based on "
                "its todos. Does NOT auto-set — user must confirm."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "project_query": {
                        "type": "string",
                        "description": "Project ID or name keywords.",
                    }
                },
                "required": ["project_query"],
            },
            fn=suggest_next_action,
        ),
    ]
