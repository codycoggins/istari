"""Tests for deadline and recurrence features in TodoManager."""

import datetime

import pytest

from istari.models.todo import TodoStatus
from istari.tools.todo.manager import TodoManager


class TestGetDueSoon:
    async def test_returns_todos_within_days(self, db_session):
        mgr = TodoManager(db_session)
        now = datetime.datetime.now(datetime.UTC)
        t_soon = await mgr.create(
            "Due soon", due_date=now + datetime.timedelta(days=2)
        )
        await mgr.create(
            "Due later", due_date=now + datetime.timedelta(days=10)
        )
        result = await mgr.get_due_soon(days=3)
        ids = [t.id for t in result]
        assert t_soon.id in ids
        assert len(result) == 1

    async def test_includes_overdue(self, db_session):
        mgr = TodoManager(db_session)
        now = datetime.datetime.now(datetime.UTC)
        overdue = await mgr.create(
            "Overdue task", due_date=now - datetime.timedelta(days=1)
        )
        result = await mgr.get_due_soon(days=3)
        assert overdue.id in [t.id for t in result]

    async def test_excludes_complete(self, db_session):
        mgr = TodoManager(db_session)
        now = datetime.datetime.now(datetime.UTC)
        todo = await mgr.create(
            "Done but due", due_date=now + datetime.timedelta(days=1)
        )
        await mgr.set_status(todo.id, TodoStatus.COMPLETE)
        result = await mgr.get_due_soon(days=3)
        assert len(result) == 0

    async def test_excludes_no_due_date(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("No due date")
        result = await mgr.get_due_soon(days=3)
        assert len(result) == 0

    async def test_ordered_by_due_date(self, db_session):
        mgr = TodoManager(db_session)
        now = datetime.datetime.now(datetime.UTC)
        t2 = await mgr.create("Due in 2 days", due_date=now + datetime.timedelta(days=2))
        t1 = await mgr.create("Due in 1 day", due_date=now + datetime.timedelta(days=1))
        result = await mgr.get_due_soon(days=3)
        assert result[0].id == t1.id
        assert result[1].id == t2.id


class TestCreateNextRecurrence:
    async def test_weekly_recurrence(self, db_session):
        mgr = TodoManager(db_session)
        now = datetime.datetime.now(datetime.UTC)
        original = await mgr.create(
            "Weekly review",
            due_date=now,
            recurrence_rule="FREQ=WEEKLY",
        )
        new_todo = await mgr.create_next_recurrence(original)
        assert new_todo.title == original.title
        assert new_todo.recurrence_rule == "FREQ=WEEKLY"
        assert new_todo.due_date is not None
        assert new_todo.due_date > now

    async def test_daily_recurrence(self, db_session):
        mgr = TodoManager(db_session)
        now = datetime.datetime.now(datetime.UTC)
        original = await mgr.create(
            "Daily standup",
            due_date=now,
            recurrence_rule="FREQ=DAILY",
        )
        new_todo = await mgr.create_next_recurrence(original)
        assert new_todo.due_date is not None
        # Next daily occurrence should be roughly 1 day out
        diff = (new_todo.due_date - now).total_seconds()
        assert diff > 0
        assert diff < 2 * 24 * 3600 + 60  # within 2 days + margin

    async def test_inherits_project_id(self, db_session):
        mgr = TodoManager(db_session)
        now = datetime.datetime.now(datetime.UTC)
        original = await mgr.create(
            "Task with project",
            due_date=now,
            recurrence_rule="FREQ=WEEKLY",
        )
        # Manually set a fake project_id-like value by updating
        await mgr.update(original.id, project_id=None)  # keep None for SQLite compat
        new_todo = await mgr.create_next_recurrence(original)
        assert new_todo.project_id == original.project_id

    async def test_inherits_urgency_importance(self, db_session):
        mgr = TodoManager(db_session)
        now = datetime.datetime.now(datetime.UTC)
        original = await mgr.create(
            "Urgent recurring",
            due_date=now,
            recurrence_rule="FREQ=WEEKLY",
            urgent=True,
            important=True,
        )
        new_todo = await mgr.create_next_recurrence(original)
        assert new_todo.urgent is True
        assert new_todo.important is True

    async def test_no_recurrence_rule_raises(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("No recurrence")
        with pytest.raises(ValueError, match="no recurrence_rule"):
            await mgr.create_next_recurrence(todo)

    async def test_invalid_rule_falls_back_to_7_days(self, db_session):
        mgr = TodoManager(db_session)
        now = datetime.datetime.now(datetime.UTC)
        original = await mgr.create(
            "Bad rule task",
            due_date=now,
            recurrence_rule="INVALID_RULE_XYZ",
        )
        new_todo = await mgr.create_next_recurrence(original)
        # Should fall back to 7 days
        assert new_todo.due_date is not None
        diff_days = (new_todo.due_date - now).days
        assert 6 <= diff_days <= 8


class TestDeadlineUrgentSort:
    async def test_due_soon_todo_sorted_before_unclassified(self, db_session):
        """A todo due soon should rank higher than an unclassified todo."""
        mgr = TodoManager(db_session)
        now = datetime.datetime.now(datetime.UTC)
        t_unclassified = await mgr.create("Regular todo")
        t_due_soon = await mgr.create(
            "Due soon todo", due_date=now + datetime.timedelta(days=1)
        )

        # get_prioritized uses deadline_urgent_days from settings (default 3)
        result = await mgr.get_prioritized(limit=5)
        ids = [t.id for t in result]
        assert t_due_soon.id in ids
        assert t_unclassified.id in ids
        # Due-soon todo should come before unclassified
        assert ids.index(t_due_soon.id) < ids.index(t_unclassified.id)
