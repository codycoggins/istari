"""TODO manager tool — CRUD for internal TODO store (internal write, not external)."""

import datetime

from sqlalchemy import and_, case, select
from sqlalchemy.ext.asyncio import AsyncSession

from istari.models.todo import Todo, TodoStatus


class TodoManager:
    """CRUD operations for TODOs backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    _ACTIONABLE = (TodoStatus.OPEN, TodoStatus.IN_PROGRESS, TodoStatus.BLOCKED)
    _VISIBLE = (TodoStatus.OPEN, TodoStatus.IN_PROGRESS, TodoStatus.BLOCKED, TodoStatus.COMPLETE)

    async def create(self, title: str, **kwargs: object) -> Todo:
        todo = Todo(title=title, status=TodoStatus.OPEN, **kwargs)
        self.session.add(todo)
        await self.session.flush()
        return todo

    async def get(self, todo_id: int) -> Todo | None:
        return await self.session.get(Todo, todo_id)

    async def list_open(self) -> list[Todo]:
        stmt = (
            select(Todo)
            .where(Todo.status.in_(self._ACTIONABLE))
            .order_by(Todo.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_visible(self) -> list[Todo]:
        """Return all non-deferred TODOs: actionable first, then completed."""
        stmt = (
            select(Todo)
            .where(Todo.status.in_(self._VISIBLE))
            .order_by(
                (Todo.status == TodoStatus.COMPLETE).asc(),
                Todo.created_at.desc(),
            )
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
        return await self.update(todo_id, status=TodoStatus.COMPLETE)

    async def set_status(self, todo_id: int, status: TodoStatus) -> Todo | None:
        return await self.update(todo_id, status=status)

    async def get_stale(self, days: int = 3) -> list[Todo]:
        """Return open/in_progress TODOs not updated in the given number of days."""
        cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days)
        stmt = (
            select(Todo)
            .where(
                Todo.status.in_((TodoStatus.OPEN, TodoStatus.IN_PROGRESS)),
                Todo.updated_at < cutoff,
            )
            .order_by(Todo.updated_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_prioritized(self, limit: int = 3) -> list[Todo]:
        """Return top TODOs: Q1 (urgent+important) → Q2 → Q3 → unclassified → Q4."""
        quadrant = case(
            (and_(Todo.urgent == True, Todo.important == True), 1),   # noqa: E712
            (Todo.important == True, 2),  # important=true, urgent=false/null  # noqa: E712
            (Todo.urgent == True, 3),     # urgent=true, important=false/null  # noqa: E712
            (and_(Todo.urgent.is_(None), Todo.important.is_(None)), 4),
            else_=5,  # Q4: both false
        )
        stmt = (
            select(Todo)
            .where(Todo.status.in_((TodoStatus.OPEN, TodoStatus.IN_PROGRESS)))
            .order_by(
                quadrant.asc(),
                Todo.priority.asc().nulls_last(),
                Todo.due_date.asc().nulls_last(),
                Todo.created_at.desc(),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_urgency_importance(
        self,
        todo_id: int,
        urgent: bool | None,
        important: bool | None,
    ) -> Todo | None:
        """Set Eisenhower urgency/importance fields on a TODO."""
        return await self.update(todo_id, urgent=urgent, important=important)
