"""Tests for TodoManager — CRUD against SQLite test DB."""

from istari.tools.todo.manager import TodoManager


class TestTodoManagerCRUD:
    async def test_create_todo(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Buy groceries")
        assert todo.id is not None
        assert todo.title == "Buy groceries"
        assert todo.status.value == "active"

    async def test_get_todo(self, db_session):
        mgr = TodoManager(db_session)
        created = await mgr.create("Read a book")
        fetched = await mgr.get(created.id)
        assert fetched is not None
        assert fetched.title == "Read a book"

    async def test_get_nonexistent_returns_none(self, db_session):
        mgr = TodoManager(db_session)
        assert await mgr.get(9999) is None

    async def test_list_active(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("Task 1")
        await mgr.create("Task 2")
        active = await mgr.list_active()
        assert len(active) == 2

    async def test_update_todo(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Old title")
        updated = await mgr.update(todo.id, title="New title")
        assert updated is not None
        assert updated.title == "New title"

    async def test_update_nonexistent_returns_none(self, db_session):
        mgr = TodoManager(db_session)
        assert await mgr.update(9999, title="nope") is None

    async def test_complete_todo(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Finish report")
        completed = await mgr.complete(todo.id)
        assert completed is not None
        assert completed.status.value == "completed"

    async def test_completed_not_in_active_list(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Will be completed")
        await mgr.complete(todo.id)
        active = await mgr.list_active()
        assert len(active) == 0


class TestTodoPrioritization:
    async def test_priority_ordering(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("Low priority", priority=3)
        await mgr.create("High priority", priority=1)
        await mgr.create("Mid priority", priority=2)
        prioritized = await mgr.get_prioritized(limit=3)
        assert prioritized[0].title == "High priority"
        assert prioritized[1].title == "Mid priority"
        assert prioritized[2].title == "Low priority"

    async def test_limit_respected(self, db_session):
        mgr = TodoManager(db_session)
        for i in range(5):
            await mgr.create(f"Task {i}")
        prioritized = await mgr.get_prioritized(limit=3)
        assert len(prioritized) == 3

    async def test_null_priority_sorted_last(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("No priority")
        await mgr.create("Has priority", priority=1)
        prioritized = await mgr.get_prioritized(limit=2)
        assert prioritized[0].title == "Has priority"
