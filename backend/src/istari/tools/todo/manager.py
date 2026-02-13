"""TODO manager tool — CRUD for internal TODO store (internal write, not external)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from istari.models.todo import Todo, TodoStatus


class TodoManager:
    """CRUD operations for TODOs backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, title: str, **kwargs: object) -> Todo:
        todo = Todo(title=title, status=TodoStatus.ACTIVE, **kwargs)  # type: ignore[arg-type]
        self.session.add(todo)
        await self.session.flush()
        return todo

    async def get(self, todo_id: int) -> Todo | None:
        return await self.session.get(Todo, todo_id)

    async def list_active(self) -> list[Todo]:
        stmt = (
            select(Todo)
            .where(Todo.status == TodoStatus.ACTIVE)
            .order_by(Todo.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, todo_id: int, **kwargs: object) -> Todo | None:
        todo = await self.get(todo_id)
        if todo is None:
            return None
        for key, value in kwargs.items():
            if hasattr(todo, key):
                setattr(todo, key, value)
        await self.session.flush()
        return todo

    async def complete(self, todo_id: int) -> Todo | None:
        return await self.update(todo_id, status=TodoStatus.COMPLETED)

    async def get_prioritized(self, limit: int = 3) -> list[Todo]:
        """Return top TODOs: explicit priority > due date > recency."""
        stmt = (
            select(Todo)
            .where(Todo.status == TodoStatus.ACTIVE)
            .order_by(
                Todo.priority.asc().nulls_last(),
                Todo.due_date.asc().nulls_last(),
                Todo.created_at.desc(),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
