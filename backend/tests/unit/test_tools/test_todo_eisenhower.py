"""Tests for Eisenhower matrix fields — model, manager sorting, and agent tools."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from istari.tools.todo.manager import TodoManager

# ─── Patch target for LLM calls inside todo agent tools ───────────────────────
_CLASSIFY = "istari.agents.tools.todo.completion"


def _llm_response(data: list[dict]) -> MagicMock:
    msg = MagicMock()
    msg.content = json.dumps(data)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ─── Model field tests ─────────────────────────────────────────────────────────


class TestEisenhowerFields:
    async def test_urgent_important_default_none(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Default task")
        assert todo.urgent is None
        assert todo.important is None

    async def test_set_urgency_importance(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Some task")
        updated = await mgr.set_urgency_importance(todo.id, urgent=True, important=True)
        assert updated is not None
        assert updated.urgent is True
        assert updated.important is True

    async def test_set_partial_fields(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Partial task")
        updated = await mgr.set_urgency_importance(todo.id, urgent=False, important=None)
        assert updated is not None
        assert updated.urgent is False
        assert updated.important is None

    async def test_set_nonexistent_returns_none(self, db_session):
        mgr = TodoManager(db_session)
        result = await mgr.set_urgency_importance(9999, urgent=True, important=True)
        assert result is None


# ─── Sorting / prioritization tests ───────────────────────────────────────────


class TestEisenhowerSorting:
    async def test_q1_before_q2(self, db_session):
        mgr = TodoManager(db_session)
        q2 = await mgr.create("Schedule me", important=True, urgent=False)
        q1 = await mgr.create("Do me now", urgent=True, important=True)
        await db_session.flush()
        prioritized = await mgr.get_prioritized(limit=2)
        assert prioritized[0].id == q1.id
        assert prioritized[1].id == q2.id

    async def test_q2_before_q3(self, db_session):
        mgr = TodoManager(db_session)
        q3 = await mgr.create("Delegate me", urgent=True, important=False)
        q2 = await mgr.create("Important not urgent", urgent=False, important=True)
        await db_session.flush()
        prioritized = await mgr.get_prioritized(limit=2)
        assert prioritized[0].id == q2.id
        assert prioritized[1].id == q3.id

    async def test_unclassified_before_q4(self, db_session):
        mgr = TodoManager(db_session)
        q4 = await mgr.create("Drop me", urgent=False, important=False)
        unclassified = await mgr.create("Unknown")
        await db_session.flush()
        prioritized = await mgr.get_prioritized(limit=2)
        assert prioritized[0].id == unclassified.id
        assert prioritized[1].id == q4.id

    async def test_full_quadrant_order(self, db_session):
        mgr = TodoManager(db_session)
        q4 = await mgr.create("Q4", urgent=False, important=False)
        unc = await mgr.create("Unclassified")
        q3 = await mgr.create("Q3", urgent=True, important=False)
        q2 = await mgr.create("Q2", urgent=False, important=True)
        q1 = await mgr.create("Q1", urgent=True, important=True)
        await db_session.flush()
        prioritized = await mgr.get_prioritized(limit=5)
        ids = [t.id for t in prioritized]
        assert ids == [q1.id, q2.id, q3.id, unc.id, q4.id]


# ─── Agent tool: create_todos with auto-classification ────────────────────────


class TestCreateTodosClassification:
    def _make_context(self):
        from istari.agents.tools.base import AgentContext
        return AgentContext()

    def _make_session_mock(self, created_todo):
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.get = AsyncMock(return_value=created_todo)
        return session

    async def test_classifies_and_updates_on_create(self, db_session):
        from istari.agents.tools.todo import make_todo_tools

        context = self._make_context()
        cls_result = [{"title": "Buy milk", "urgent": False, "important": True, "uncertain": False}]

        with patch(_CLASSIFY, new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _llm_response(cls_result)
            tools = make_todo_tools(db_session, context)
            create_fn = next(t.fn for t in tools if t.name == "create_todos")
            result = await create_fn(titles=["Buy milk"])

        assert 'Added TODO: "Buy milk"' in result
        assert "urgent" not in result  # no uncertain flag

        # Verify fields were set
        from istari.tools.todo.manager import TodoManager
        mgr = TodoManager(db_session)
        todos = await mgr.list_open()
        assert todos[0].important is True
        assert todos[0].urgent is False

    async def test_flags_uncertain_for_user_clarification(self, db_session):
        from istari.agents.tools.todo import make_todo_tools

        context = self._make_context()
        cls_result = [{"title": "Foo bar", "urgent": None, "important": None, "uncertain": True}]

        with patch(_CLASSIFY, new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _llm_response(cls_result)
            tools = make_todo_tools(db_session, context)
            create_fn = next(t.fn for t in tools if t.name == "create_todos")
            result = await create_fn(titles=["Foo bar"])

        assert "wasn't sure" in result
        assert "Foo bar" in result

    async def test_classification_failure_does_not_raise(self, db_session):
        from istari.agents.tools.todo import make_todo_tools

        context = self._make_context()

        with patch(_CLASSIFY, new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM down")
            tools = make_todo_tools(db_session, context)
            create_fn = next(t.fn for t in tools if t.name == "create_todos")
            result = await create_fn(titles=["Safe task"])

        assert "Added TODO" in result  # still created


# ─── Agent tool: update_todo_priority ─────────────────────────────────────────


class TestUpdateTodoPriority:
    def _make_context(self):
        from istari.agents.tools.base import AgentContext
        return AgentContext()

    async def test_update_by_id(self, db_session):
        from istari.agents.tools.todo import make_todo_tools
        from istari.tools.todo.manager import TodoManager

        mgr = TodoManager(db_session)
        todo = await mgr.create("Fix outage")
        await db_session.flush()

        context = self._make_context()
        tools = make_todo_tools(db_session, context)
        fn = next(t.fn for t in tools if t.name == "update_todo_priority")
        result = await fn(query=str(todo.id), urgent=True, important=True)

        assert "Q1" in result
        refreshed = await mgr.get(todo.id)
        assert refreshed.urgent is True
        assert refreshed.important is True

    async def test_update_by_title_match(self, db_session):
        from istari.agents.tools.todo import make_todo_tools
        from istari.tools.todo.manager import TodoManager

        mgr = TodoManager(db_session)
        await mgr.create("Write blog post")
        await db_session.flush()

        context = self._make_context()
        tools = make_todo_tools(db_session, context)
        fn = next(t.fn for t in tools if t.name == "update_todo_priority")
        result = await fn(query="blog post", urgent=False, important=True)

        assert "Q2" in result

    async def test_update_no_match(self, db_session):
        from istari.agents.tools.todo import make_todo_tools

        context = self._make_context()
        tools = make_todo_tools(db_session, context)
        fn = next(t.fn for t in tools if t.name == "update_todo_priority")
        result = await fn(query="nonexistent xyz", urgent=True, important=True)

        assert "No TODOs found" in result


# ─── Agent tool: get_priorities shows quadrant labels ─────────────────────────


class TestGetPrioritiesQuadrants:
    async def test_shows_quadrant_label(self, db_session):
        from istari.agents.tools.base import AgentContext
        from istari.agents.tools.todo import make_todo_tools
        from istari.tools.todo.manager import TodoManager

        mgr = TodoManager(db_session)
        await mgr.create("Critical task", urgent=True, important=True)
        await db_session.flush()

        context = AgentContext()
        tools = make_todo_tools(db_session, context)
        fn = next(t.fn for t in tools if t.name == "get_priorities")
        result = await fn()

        assert "Q1" in result
        assert "Do Now" in result

    async def test_no_label_for_unclassified(self, db_session):
        from istari.agents.tools.base import AgentContext
        from istari.agents.tools.todo import make_todo_tools
        from istari.tools.todo.manager import TodoManager

        mgr = TodoManager(db_session)
        await mgr.create("Unclassified task")
        await db_session.flush()

        context = AgentContext()
        tools = make_todo_tools(db_session, context)
        fn = next(t.fn for t in tools if t.name == "get_priorities")
        result = await fn()

        assert "Unclassified task" in result
        assert "Q1" not in result
        assert "Q2" not in result
