"""Tests for the ReAct chat agent loop (run_agent) — edge cases and wiring."""

import json
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from istari.agents.chat import _format_tool_status, build_tools, run_agent
from istari.agents.tools.base import AgentContext

# ── Mock response helpers ─────────────────────────────────────────────────────


def _tool_response(tool_name: str, arguments: dict, call_id: str = "call_1"):
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(arguments)
    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _text_response(content: str):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@contextmanager
def _patch_llm():
    """Patch AsyncOpenAI and yield the chat.completions.create AsyncMock.

    Tests set .return_value / .side_effect on the yielded mock and inspect
    .call_args.kwargs["messages"] exactly as before.
    """
    client = MagicMock()
    create = AsyncMock()
    client.chat.completions.create = create
    with patch("istari.llm.router.AsyncOpenAI", return_value=client):
        yield create


# ── Max turns limit ───────────────────────────────────────────────────────────


class TestMaxTurns:
    async def test_max_turns_returns_fallback(self, db_session):
        """If the LLM keeps calling tools without a final reply, we give up gracefully."""
        from istari.agents.chat import _MAX_TURNS

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        # Always return a tool call — never a final text response
        tool_resp = _tool_response("list_todos", {})

        with _patch_llm() as mock_llm:
            mock_llm.return_value = tool_resp
            result = await run_agent("loop forever", [], tools, system_prompt="You are Istari.")

        assert mock_llm.call_count == _MAX_TURNS
        assert "wasn't able" in result.lower() or "rephrase" in result.lower()


# ── Unknown tool ──────────────────────────────────────────────────────────────


class TestUnknownTool:
    async def test_unknown_tool_does_not_raise(self, db_session):
        """If the LLM hallucinates a tool name, the loop recovers cleanly."""
        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        bad_tool = _tool_response("nonexistent_tool_xyz", {"arg": "val"})
        final = _text_response("Sorry, I couldn't do that.")

        with _patch_llm() as mock_llm:
            mock_llm.side_effect = [bad_tool, final]
            result = await run_agent("do something", [], tools, system_prompt="You are Istari.")

        assert result == "Sorry, I couldn't do that."


# ── Tool raises an exception ──────────────────────────────────────────────────


class TestToolException:
    async def test_tool_error_continues_loop(self, db_session):
        """If a tool raises, the error is captured as a result and the loop continues."""
        # Inject a tool that always raises
        from istari.agents.tools.base import AgentTool

        async def exploding_tool() -> str:
            raise RuntimeError("tool exploded")

        boom = AgentTool(
            name="boom",
            description="Always fails",
            parameters={"type": "object", "properties": {}, "required": []},
            fn=exploding_tool,
        )

        tools = [boom]
        call_resp = _tool_response("boom", {})
        final = _text_response("I hit an error but recovered.")

        with _patch_llm() as mock_llm:
            mock_llm.side_effect = [call_resp, final]
            result = await run_agent("trigger boom", [], tools, system_prompt="You are Istari.")

        assert result == "I hit an error but recovered."


# ── History threading ─────────────────────────────────────────────────────────


class TestHistory:
    async def test_history_included_in_messages(self, db_session):
        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        history = [
            {"role": "user", "content": "Earlier question"},
            {"role": "assistant", "content": "Earlier answer"},
        ]

        with _patch_llm() as mock_llm:
            mock_llm.return_value = _text_response("Got it!")
            await run_agent("Follow-up question", history, tools, system_prompt="You are Istari.")

        messages = mock_llm.call_args.kwargs["messages"]
        contents = [m["content"] for m in messages]
        assert "Earlier question" in contents
        assert "Earlier answer" in contents
        assert "Follow-up question" in contents

    async def test_system_prompt_is_first_message(self, db_session):
        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        with _patch_llm() as mock_llm:
            mock_llm.return_value = _text_response("Hi!")
            await run_agent("Hello", [], tools, system_prompt="CUSTOM SOUL")

        messages = mock_llm.call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert "CUSTOM SOUL" in messages[0]["content"]

    async def test_user_message_is_last(self, db_session):
        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        with _patch_llm() as mock_llm:
            mock_llm.return_value = _text_response("Hi!")
            await run_agent("My question", [], tools, system_prompt="You are Istari.")

        messages = mock_llm.call_args.kwargs["messages"]
        last = messages[-1]
        assert last["role"] == "user"
        assert last["content"] == "My question"


# ── build_tools wiring ────────────────────────────────────────────────────────


class TestBuildTools:
    def test_expected_tools_present(self, db_session):
        ctx = AgentContext()
        tools = build_tools(db_session, ctx)
        names = {t.name for t in tools}
        assert "create_todos" in names
        assert "list_todos" in names
        assert "update_todo_status" in names
        assert "get_priorities" in names
        assert "remember" in names
        assert "search_memory" in names
        assert "read_file" in names
        assert "search_files" in names

    def test_no_duplicate_names(self, db_session):
        ctx = AgentContext()
        tools = build_tools(db_session, ctx)
        names = [t.name for t in tools]
        assert len(names) == len(set(names))


# ── _format_tool_status ───────────────────────────────────────────────────────


class TestFormatToolStatus:
    def test_check_email_no_query(self):
        assert _format_tool_status("check_email", {}) == "Checking Gmail for unread messages..."

    def test_check_email_with_query(self):
        result = _format_tool_status("check_email", {"query": "invoice"})
        assert result == "Searching Gmail for 'invoice'..."

    def test_check_calendar_no_query(self):
        assert _format_tool_status("check_calendar", {}) == "Checking your calendar..."

    def test_check_calendar_with_query(self):
        result = _format_tool_status("check_calendar", {"query": "standup"})
        assert result == "Searching calendar for 'standup'..."

    def test_create_todos_single(self):
        result = _format_tool_status("create_todos", {"titles": ["Buy groceries"]})
        assert result == "Creating task: 'Buy groceries'..."

    def test_create_todos_multiple(self):
        result = _format_tool_status("create_todos", {"titles": ["A", "B", "C"]})
        assert result == "Creating 3 tasks..."

    def test_create_todos_empty(self):
        result = _format_tool_status("create_todos", {"titles": []})
        assert result == "Creating 0 tasks..."

    def test_list_todos_open(self):
        result = _format_tool_status("list_todos", {"filter": "open"})
        assert result == "Looking at your open task list..."

    def test_list_todos_all(self):
        result = _format_tool_status("list_todos", {"filter": "all"})
        assert result == "Looking at your all task list..."

    def test_list_todos_complete(self):
        result = _format_tool_status("list_todos", {"filter": "complete"})
        assert result == "Looking at your completed task list..."

    def test_list_todos_default(self):
        result = _format_tool_status("list_todos", {})
        assert result == "Looking at your open task list..."

    def test_update_todo_status(self):
        result = _format_tool_status("update_todo_status", {"status": "complete"})
        assert result == "Updating task status to 'complete'..."

    def test_update_todo_priority(self):
        assert _format_tool_status("update_todo_priority", {}) == "Updating task priority..."

    def test_get_priorities(self):
        assert _format_tool_status("get_priorities", {}) == "Getting your priorities..."

    def test_set_today_focus(self):
        assert _format_tool_status("set_today_focus", {}) == "Setting today's focus tasks..."

    def test_get_today_focus(self):
        assert _format_tool_status("get_today_focus", {}) == "Getting today's focus tasks..."

    def test_remember_with_fact(self):
        result = _format_tool_status("remember", {"fact": "I like tea"})
        assert result == "Saving to memory: 'I like tea'..."

    def test_remember_no_fact(self):
        assert _format_tool_status("remember", {}) == "Saving to memory..."

    def test_search_memory_with_query(self):
        result = _format_tool_status("search_memory", {"query": "dentist"})
        assert result == "Searching memory for 'dentist'..."

    def test_search_memory_no_query(self):
        assert _format_tool_status("search_memory", {}) == "Searching memory..."

    def test_read_file_with_path(self):
        result = _format_tool_status("read_file", {"path": "/tmp/notes.txt"})
        assert result == "Reading file: /tmp/notes.txt..."

    def test_read_file_no_path(self):
        assert _format_tool_status("read_file", {}) == "Reading file..."

    def test_search_files_with_query_and_dir(self):
        result = _format_tool_status("search_files", {"query": "budget", "directory": "~/docs"})
        assert result == "Searching files in ~/docs for 'budget'..."

    def test_search_files_with_query_no_dir(self):
        result = _format_tool_status("search_files", {"query": "budget"})
        assert result == "Searching files for 'budget'..."

    def test_search_files_no_args(self):
        assert _format_tool_status("search_files", {}) == "Searching files..."

    def test_unknown_tool_fallback(self):
        result = _format_tool_status("some_custom_tool", {})
        assert result == "Running Some Custom Tool..."

    def test_unknown_tool_single_word(self):
        result = _format_tool_status("analyze", {})
        assert result == "Running Analyze..."

    def test_create_todos_title_truncated_at_40(self):
        long_title = "A" * 50
        result = _format_tool_status("create_todos", {"titles": [long_title]})
        assert "A" * 40 in result
        assert "A" * 41 not in result


# ── status_callback in run_agent ─────────────────────────────────────────────


class TestStatusCallback:
    async def test_thinking_fires_before_llm_call(self, db_session):
        """status_callback("Thinking...") is called once before the LLM call."""
        ctx = AgentContext()
        tools = build_tools(db_session, ctx)
        callback = AsyncMock()

        with _patch_llm() as mock_llm:
            mock_llm.return_value = _text_response("Done!")
            await run_agent(
                "hello", [], tools,
                system_prompt="You are Istari.",
                status_callback=callback,
            )

        # At minimum, "Thinking..." was sent once before the single LLM call
        assert callback.call_count >= 1
        assert callback.call_args_list[0].args[0] == "Thinking..."

    async def test_tool_status_fires_before_tool_execution(self, db_session):
        """For a tool call turn, tool-specific status fires after Thinking..."""
        from istari.agents.tools.base import AgentTool

        executed = []

        async def my_tool() -> str:
            executed.append("ran")
            return "done"

        tool = AgentTool(
            name="get_priorities",
            description="Get priorities",
            parameters={"type": "object", "properties": {}, "required": []},
            fn=my_tool,
        )

        call_resp = _tool_response("get_priorities", {})
        final = _text_response("Here are your priorities.")
        callback_calls: list[str] = []

        async def capturing_callback(text: str) -> None:
            callback_calls.append(text)

        with _patch_llm() as mock_llm:
            mock_llm.side_effect = [call_resp, final]
            await run_agent(
                "what are my priorities?", [], [tool],
                system_prompt="You are Istari.",
                status_callback=capturing_callback,
            )

        # turn 1: "Thinking..." then "Getting your priorities..."
        # turn 2: "Thinking..." then final text (no tool status)
        assert "Thinking..." in callback_calls
        assert "Getting your priorities..." in callback_calls
        # Tool status comes after the first "Thinking..."
        thinking_idx = callback_calls.index("Thinking...")
        prio_idx = callback_calls.index("Getting your priorities...")
        assert thinking_idx < prio_idx

    async def test_none_callback_does_not_raise(self, db_session):
        """Passing no callback (None) should work exactly as before."""
        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        with _patch_llm() as mock_llm:
            mock_llm.return_value = _text_response("All good.")
            result = await run_agent(
                "test", [], tools,
                system_prompt="You are Istari.",
                status_callback=None,
            )

        assert result == "All good."
