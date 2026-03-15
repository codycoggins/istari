"""TODO manager tool — CRUD for internal TODO store (internal write, not external)."""

import datetime
import logging
from typing import Any

from dateutil.rrule import rrulestr
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from istari.models.todo import Todo, TodoStatus

logger = logging.getLogger(__name__)


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

    def _quadrant_sort(self, urgent_days: int = 0) -> Any:
        """Quadrant sort expression, optionally treating deadline-due todos as urgent."""
        if urgent_days > 0:
            cutoff = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=urgent_days)
            deadline_urgent = and_(Todo.due_date.isnot(None), Todo.due_date <= cutoff)
            effective_urgent = or_(Todo.urgent == True, deadline_urgent)  # noqa: E712
            return case(
                (and_(effective_urgent, Todo.important == True), 1),  # noqa: E712
                (Todo.important == True, 2),  # noqa: E712
                (effective_urgent, 3),
                (and_(Todo.urgent.is_(None), Todo.important.is_(None)), 4),
                else_=5,  # Q4: both false
            )
        return case(
            (and_(Todo.urgent == True, Todo.important == True), 1),  # noqa: E712
            (Todo.important == True, 2),  # noqa: E712
            (Todo.urgent == True, 3),  # noqa: E712
            (and_(Todo.urgent.is_(None), Todo.important.is_(None)), 4),
            else_=5,  # Q4: both false
        )

    async def list_visible(self) -> list[Todo]:
        """Return all non-deferred TODOs: complete last, overdue first, then by quadrant."""
        now = func.now()
        overdue_first = case(
            (and_(Todo.due_date.isnot(None), Todo.due_date < now), 0),
            else_=1,
        )
        quadrant = self._quadrant_sort()
        stmt = (
            select(Todo)
            .where(Todo.status.in_(self._VISIBLE))
            .order_by(
                (Todo.status == TodoStatus.COMPLETE).asc(),
                overdue_first.asc(),
                quadrant.asc(),
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

    async def get_due_soon(self, days: int = 3) -> list[Todo]:
        """Return actionable TODOs with due_date within the next N days (includes overdue)."""
        cutoff = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=days)
        stmt = (
            select(Todo)
            .where(
                Todo.status.in_(self._ACTIONABLE),
                Todo.due_date.isnot(None),
                Todo.due_date <= cutoff,
            )
            .order_by(Todo.due_date.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_prioritized(
        self, limit: int = 3, exclude_ids: list[int] | None = None
    ) -> list[Todo]:
        """Return top TODOs: deadline-due treated as urgent; Q1 → Q2 → Q3 → unclassified → Q4."""
        from istari.config.settings import settings

        quadrant = self._quadrant_sort(urgent_days=settings.deadline_urgent_days)
        now = func.now()
        overdue_first = case(
            (and_(Todo.due_date.isnot(None), Todo.due_date < now), 0),
            else_=1,
        )
        filters = [Todo.status.in_((TodoStatus.OPEN, TodoStatus.IN_PROGRESS))]
        if exclude_ids:
            filters.append(Todo.id.not_in(exclude_ids))
        stmt = (
            select(Todo)
            .where(*filters)
            .order_by(
                quadrant.asc(),
                overdue_first.asc(),
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

    async def list_today(self) -> list[Todo]:
        """Return actionable TODOs focused for today, sorted by quadrant then recency."""
        today = datetime.date.today()
        quadrant = self._quadrant_sort()
        stmt = (
            select(Todo)
            .where(Todo.today_date == today, Todo.status.in_(self._ACTIONABLE))
            .order_by(quadrant.asc(), Todo.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_today(self, todo_id: int, flag: bool) -> Todo | None:
        """Set or clear today_date on a TODO. flag=True sets today; flag=False clears."""
        value = datetime.date.today() if flag else None
        return await self.update(todo_id, today_date=value)

    async def create_next_recurrence(self, todo: Todo) -> Todo:
        """Create the next recurrence instance for a completed recurring todo.

        Parses the RRULE from todo.recurrence_rule, finds the next occurrence
        after the current due date (or now), and creates a new Todo inheriting key fields.
        """
        if not todo.recurrence_rule:
            raise ValueError("Todo has no recurrence_rule")

        now = datetime.datetime.now(datetime.UTC)
        base_dt = todo.due_date if todo.due_date else now

        try:
            # Strip timezone for rrulestr (it returns naive datetimes)
            base_naive = base_dt.replace(tzinfo=None) if base_dt.tzinfo else base_dt
            rule = rrulestr(todo.recurrence_rule, dtstart=base_naive, ignoretz=True)
            # Find next occurrence strictly after base (or after now if base is past)
            after_naive = max(base_naive, now.replace(tzinfo=None))
            next_dt_naive = rule.after(after_naive, inc=False)
        except Exception:
            logger.warning(
                "Failed to parse recurrence_rule %r for todo %d",
                todo.recurrence_rule,
                todo.id,
                exc_info=True,
            )
            next_dt_naive = None

        if next_dt_naive is None:
            next_dt_naive = now.replace(tzinfo=None) + datetime.timedelta(days=7)

        # Restore UTC timezone
        next_dt = next_dt_naive.replace(tzinfo=datetime.UTC)

        new_todo = await self.create(
            title=todo.title,
            body=todo.body,
            source=todo.source,
            source_link=todo.source_link,
            due_date=next_dt,
            recurrence_rule=todo.recurrence_rule,
            urgent=todo.urgent,
            important=todo.important,
            project_id=todo.project_id,
        )
        return new_todo
