"""Project manager — CRUD for the Projects table."""

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from istari.models.project import Project, ProjectStatus
from istari.models.todo import Todo, TodoStatus


class ProjectManager:
    """CRUD operations for Projects backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        name: str,
        description: str = "",
        goal: str = "",
        status: ProjectStatus = ProjectStatus.active,
    ) -> Project:
        project = Project(
            name=name,
            description=description or None,
            goal=goal or None,
            status=status,
        )
        self.session.add(project)
        await self.session.flush()
        return project

    async def get(self, project_id: int) -> Project | None:
        return await self.session.get(Project, project_id)

    async def list_active(self) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.status == ProjectStatus.active)
            .order_by(Project.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self) -> list[Project]:
        stmt = select(Project).order_by(Project.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name(self, query: str) -> list[Project]:
        """ILIKE search on project name."""
        stmt = (
            select(Project)
            .where(Project.name.ilike(f"%{query}%"))
            .order_by(Project.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, project_id: int, **kwargs: object) -> Project | None:
        project = await self.get(project_id)
        if project is None:
            return None
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)
        await self.session.flush()
        return project

    async def set_next_action(self, project_id: int, todo_id: int | None) -> Project:
        project = await self.get(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")
        project.next_action_id = todo_id
        await self.session.flush()
        return project

    async def set_status(self, project_id: int, status: ProjectStatus) -> Project:
        project = await self.get(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")
        project.status = status
        await self.session.flush()
        return project

    async def get_stale(self, days: int = 7) -> list[Project]:
        """Return active projects with no associated todo updated in the last N days."""
        cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days)

        # Subquery: project IDs that have at least one recently-updated todo
        recent_sub = (
            select(Todo.project_id)
            .where(
                Todo.project_id.is_not(None),
                Todo.status.in_((TodoStatus.OPEN, TodoStatus.IN_PROGRESS)),
                Todo.updated_at >= cutoff,
            )
            .scalar_subquery()
        )

        stmt = (
            select(Project)
            .where(
                Project.status == ProjectStatus.active,
                Project.id.not_in(recent_sub),
            )
            .order_by(Project.updated_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_todos(self, project_id: int) -> Project | None:
        """Eagerly load the todos relationship."""
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.todos))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
