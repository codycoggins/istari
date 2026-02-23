"""Tests for agent tool functions and the ReAct agent loop."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from istari.agents.tools.base import AgentContext, normalize_status
from istari.agents.tools.memory import make_memory_tools
from istari.agents.tools.todo import make_todo_tools
from istari.models.todo import TodoStatus
from istari.tools.todo.manager import TodoManager

# ---------------------------------------------------------------------------
# normalize_status
# ---------------------------------------------------------------------------

class TestNormalizeStatus:
    def test_passthrough_valid(self):
        assert normalize_status("complete") == "complete"
        assert normalize_status("in_progress") == "in_progress"
        assert normalize_status("blocked") == "blocked"
        assert normalize_status("deferred") == "deferred"
        assert normalize_status("open") == "open"

    def test_done_maps_to_complete(self):
        assert normalize_status("done") == "complete"

    def test_finished_maps_to_complete(self):
        assert normalize_status("finished") == "complete"

    def test_started_maps_to_in_progress(self):
        assert normalize_status("started") == "in_progress"

    def test_stuck_maps_to_blocked(self):
        assert normalize_status("stuck") == "blocked"

    def test_later_maps_to_deferred(self):
        assert normalize_status("later") == "deferred"

    def test_case_insensitive(self):
        assert normalize_status("Done") == "complete"
        assert normalize_status("FINISHED") == "complete"

    def test_strips_whitespace(self):
        assert normalize_status("  done  ") == "complete"

    def test_unknown_passthrough(self):
        assert normalize_status("whatever") == "whatever"


# ---------------------------------------------------------------------------
# Todo tools
# ---------------------------------------------------------------------------

class TestCreateTodosTool:
    async def test_creates_single_todo(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["create_todos"].fn(titles=["Buy groceries"])

        assert "Buy groceries" in result
        assert ctx.todo_created is True

        mgr = TodoManager(db_session)
        todos = await mgr.list_open()
        assert any(t.title == "Buy groceries" for t in todos)

    async def test_creates_multiple_todos(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        titles = [
            "Eat breakfast on Monday",
            "Eat breakfast on Tuesday",
            "Eat breakfast on Wednesday",
        ]
        result = await tools["create_todos"].fn(titles=titles)

        assert "3" in result
        assert ctx.todo_created is True

        mgr = TodoManager(db_session)
        todos = await mgr.list_open()
        created_titles = {t.title for t in todos}
        for title in titles:
            assert title in created_titles

    async def test_create_trims_whitespace(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        await tools["create_todos"].fn(titles=["  Fix the bug  "])

        mgr = TodoManager(db_session)
        todos = await mgr.list_open()
        assert any(t.title == "Fix the bug" for t in todos)


class TestUpdateTodoStatusTool:
    async def test_update_by_numeric_id(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Pay bills")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["update_todo_status"].fn(
            query=str(todo.id), status="complete"
        )

        assert "complete" in result
        assert ctx.todo_updated is True

        updated = await mgr.get(todo.id)
        assert updated.status == TodoStatus.COMPLETE

    async def test_update_by_pattern_single_match(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("Call the dentist")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["update_todo_status"].fn(query="dentist", status="complete")

        assert "complete" in result
        assert ctx.todo_updated is True

    async def test_update_by_pattern_bulk(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("Eat breakfast on Monday")
        await mgr.create("Eat breakfast on Tuesday")
        await mgr.create("Eat breakfast on Wednesday")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["update_todo_status"].fn(
            query="eat breakfast", status="complete"
        )

        assert "3" in result
        assert ctx.todo_updated is True

        todos = await mgr.list_visible()
        breakfast_todos = [t for t in todos if "breakfast" in t.title.lower()]
        assert all(t.status == TodoStatus.COMPLETE for t in breakfast_todos)

    async def test_update_with_synonym_done(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("Review PR")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["update_todo_status"].fn(query="Review PR", status="done")

        assert "complete" in result
        assert ctx.todo_updated is True

    async def test_update_no_match_returns_message(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["update_todo_status"].fn(
            query="nonexistent task xyz", status="complete"
        )

        assert "No TODOs found" in result
        assert ctx.todo_updated is False

    async def test_update_invalid_status_returns_message(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["update_todo_status"].fn(
            query="anything", status="banana"
        )

        assert "not a valid status" in result.lower() or "valid" in result.lower()
        assert ctx.todo_updated is False


class TestListTodosTool:
    async def test_returns_open_todos_by_default(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("Task A")
        await mgr.create("Task B")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["list_todos"].fn(filter="open")

        assert "Task A" in result
        assert "Task B" in result

    async def test_returns_message_when_empty(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["list_todos"].fn(filter="open")

        assert "No TODOs" in result

    async def test_complete_filter(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Done task")
        await mgr.set_status(todo.id, TodoStatus.COMPLETE)
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["list_todos"].fn(filter="complete")

        assert "Done task" in result


class TestGetPrioritiesTool:
    async def test_returns_top_todos(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("High priority task", priority=1)
        await mgr.create("Low priority task", priority=5)
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["get_priorities"].fn()

        assert "High priority task" in result

    async def test_no_todos_returns_message(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["get_priorities"].fn()

        assert "No active" in result


# ---------------------------------------------------------------------------
# Memory tools
# ---------------------------------------------------------------------------

class TestMemoryTools:
    async def test_remember_stores_and_sets_flag(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_memory_tools(db_session, ctx)}
        result = await tools["remember"].fn(fact="I prefer dark mode")

        assert "dark mode" in result
        assert ctx.memory_created is True

    async def test_search_memory_finds_stored(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_memory_tools(db_session, ctx)}
        await tools["remember"].fn(fact="Favourite colour is blue")

        result = await tools["search_memory"].fn(query="colour")
        assert "blue" in result

    async def test_search_memory_no_match(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_memory_tools(db_session, ctx)}
        result = await tools["search_memory"].fn(query="nonexistent xyz")

        assert "No memories" in result


# ---------------------------------------------------------------------------
# Tool schema format
# ---------------------------------------------------------------------------

class TestToolSchemas:
    def test_all_tools_have_valid_openai_schema(self, db_session):
        from istari.agents.chat import build_tools

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)
        for tool in tools:
            schema = tool.to_openai_schema()
            assert schema["type"] == "function"
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_no_duplicate_tool_names(self, db_session):
        from istari.agents.chat import build_tools

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)
        names = [t.name for t in tools]
        assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# run_agent — mocked LLM
# ---------------------------------------------------------------------------

def _make_tool_call_response(tool_name: str, arguments: dict, call_id: str = "call_1"):
    """Build a mock LiteLLM response that requests a tool call."""
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(arguments)

    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]

    choice = MagicMock()
    choice.message = msg

    response = MagicMock()
    response.choices = [choice]
    return response


def _make_text_response(content: str):
    """Build a mock LiteLLM response with a final text reply."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None

    choice = MagicMock()
    choice.message = msg

    response = MagicMock()
    response.choices = [choice]
    return response


class TestRunAgent:
    async def test_direct_response_no_tools(self, db_session):
        from istari.agents.chat import build_tools, run_agent

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        with patch("istari.llm.router.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _make_text_response("Hello, how can I help?")
            result = await run_agent("Hi there", [], tools, system_prompt="You are Istari.")

        assert result == "Hello, how can I help?"

    async def test_create_todos_via_tool_call(self, db_session):
        from istari.agents.chat import build_tools, run_agent

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        tool_resp = _make_tool_call_response(
            "create_todos", {"titles": ["Buy milk", "Walk the dog"]}
        )
        final_resp = _make_text_response("Done! I've added 2 TODOs for you.")

        with patch("istari.llm.router.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = [tool_resp, final_resp]
            await run_agent(
                "Add todos: buy milk and walk the dog", [], tools,
                system_prompt="You are Istari.",
            )

        assert ctx.todo_created is True
        mgr = TodoManager(db_session)
        open_todos = await mgr.list_open()
        titles = {t.title for t in open_todos}
        assert "Buy milk" in titles
        assert "Walk the dog" in titles

    async def test_llm_error_returns_friendly_message(self, db_session):
        from istari.agents.chat import build_tools, run_agent

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        with patch("istari.llm.router.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("API unavailable")
            result = await run_agent(
                "What should I do?", [], tools, system_prompt="You are Istari.",
            )

        assert "trouble" in result.lower() or "try again" in result.lower()

    async def test_system_prompt_passed_to_llm(self, db_session):
        from istari.agents.chat import build_tools, run_agent

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        with patch("istari.llm.router.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _make_text_response("Got it!")
            await run_agent("Hi", [], tools, system_prompt="The user's name is Cody.")

        call_messages = mock_llm.call_args.kwargs["messages"]
        system_msg = call_messages[0]
        assert "Cody" in system_msg["content"]
