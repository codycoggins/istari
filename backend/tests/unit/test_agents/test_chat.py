"""Tests for the ReAct chat agent loop (run_agent) — edge cases and wiring."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from istari.agents.chat import build_tools, run_agent
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


_LLM = "istari.llm.router.litellm.acompletion"


# ── Max turns limit ───────────────────────────────────────────────────────────


class TestMaxTurns:
    async def test_max_turns_returns_fallback(self, db_session):
        """If the LLM keeps calling tools without a final reply, we give up gracefully."""
        from istari.agents.chat import _MAX_TURNS

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        # Always return a tool call — never a final text response
        tool_resp = _tool_response("list_todos", {})

        with patch(_LLM, new_callable=AsyncMock) as mock_llm:
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

        with patch(_LLM, new_callable=AsyncMock) as mock_llm:
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

        with patch(_LLM, new_callable=AsyncMock) as mock_llm:
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

        with patch(_LLM, new_callable=AsyncMock) as mock_llm:
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

        with patch(_LLM, new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _text_response("Hi!")
            await run_agent("Hello", [], tools, system_prompt="CUSTOM SOUL")

        messages = mock_llm.call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert "CUSTOM SOUL" in messages[0]["content"]

    async def test_user_message_is_last(self, db_session):
        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        with patch(_LLM, new_callable=AsyncMock) as mock_llm:
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
