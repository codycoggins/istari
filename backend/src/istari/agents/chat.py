"""Chat agent — ReAct tool-calling loop for interactive user conversations.

Architecture: the LLM receives a set of tools and reasons across multiple turns:
  1. User message arrives
  2. LLM decides which tool(s) to call (or responds directly)
  3. Tools execute and return results
  4. LLM sees results, may call more tools or produce a final response
  5. Loop continues until a final text response or max_turns is reached

Tools are bound to the current DB session at WebSocket connect time via closures,
so the agent has no direct DB access — all persistence goes through tool functions.
"""

import json
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from istari.agents.tools.base import AgentContext, AgentTool

logger = logging.getLogger(__name__)

_MAX_TURNS = 8

_SYSTEM_PROMPT_TEMPLATE = """\
You are Istari, a personal AI assistant.{name_line}
You help the user manage their TODOs, memories, email, and calendar.

You have tools available. Use them whenever the user's request involves:
- Viewing, adding, or updating TODOs or tasks
- Remembering facts or preferences
- Checking email or calendar

Guidelines:
- For any request to add a reminder, task, or action item: use create_todos.
- For bulk operations (e.g. "add five todos"): call create_todos with all titles in one call.
- For status updates (e.g. "mark as done"): use update_todo_status. "done" and "finished" \
map to "complete".
- When the user asks what to work on: use get_priorities.
- After using a tool, summarize the result conversationally — do not just repeat the raw output.
- Be concise and action-oriented.\
"""


def _build_system_prompt(user_name: str = "") -> str:
    name_line = f" The user's name is {user_name}." if user_name else ""
    return _SYSTEM_PROMPT_TEMPLATE.format(name_line=name_line)


def build_tools(session: "AsyncSession", context: AgentContext) -> list[AgentTool]:
    """Assemble all agent tools bound to this session."""
    from istari.agents.tools.calendar import make_calendar_tools
    from istari.agents.tools.gmail import make_gmail_tools
    from istari.agents.tools.memory import make_memory_tools
    from istari.agents.tools.todo import make_todo_tools

    return [
        *make_todo_tools(session, context),
        *make_memory_tools(session, context),
        *make_gmail_tools(),
        *make_calendar_tools(),
    ]


async def run_agent(
    user_message: str,
    history: list[dict],
    tools: list[AgentTool],
    *,
    user_name: str = "",
) -> str:
    """Run the ReAct agent loop and return the final response text."""
    from istari.llm.router import completion

    tool_map = {t.name: t for t in tools}
    tool_schemas = [t.to_openai_schema() for t in tools]

    messages: list[dict] = [
        {"role": "system", "content": _build_system_prompt(user_name)},
        *history,
        {"role": "user", "content": user_message},
    ]

    agent_start = time.monotonic()
    logger.info("Agent start | user=%r | tools=%s", user_message[:80], [t.name for t in tools])

    for turn in range(_MAX_TURNS):
        logger.debug("Agent turn %d/%d | %d msgs", turn + 1, _MAX_TURNS, len(messages))

        try:
            result = await completion(
                "chat_response",
                messages,
                tools=tool_schemas,
                tool_choice="auto",
            )
        except Exception:
            logger.exception("LLM call failed on turn %d", turn + 1)
            return "I'm having trouble connecting right now. Please try again in a moment."

        choice = result.choices[0]
        msg = choice.message

        # No tool calls — this is the final response
        if not getattr(msg, "tool_calls", None):
            elapsed = time.monotonic() - agent_start
            logger.info("Agent done | turns=%d | %.2fs", turn + 1, elapsed)
            return msg.content or ""

        # Add assistant message with tool calls to context
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ],
        })

        # Execute each tool call and append results
        for tc in msg.tool_calls:
            tool_name = tc.function.name
            tool = tool_map.get(tool_name)
            logger.debug("Tool args | %s | %s", tool_name, tc.function.arguments)

            if tool is None:
                logger.warning("Tool called but not found: %r", tool_name)
                tool_result = f"Unknown tool: {tool_name}"
            else:
                t0 = time.monotonic()
                try:
                    args = json.loads(tc.function.arguments)
                    tool_result = await tool.fn(**args)
                    elapsed_ms = (time.monotonic() - t0) * 1000
                    logger.info(
                        "Tool call | %-24s | %.0fms | %d chars returned",
                        tool_name, elapsed_ms, len(tool_result),
                    )
                except Exception as exc:
                    elapsed_ms = (time.monotonic() - t0) * 1000
                    logger.exception(
                        "Tool error | %-24s | %.0fms | %s", tool_name, elapsed_ms, exc
                    )
                    tool_result = f"Tool error: {exc}"

            logger.debug("Tool result | %s | %r", tool_name, tool_result[:200])
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_result,
            })

    elapsed = time.monotonic() - agent_start
    logger.warning("Agent max turns reached | %d turns | %.2fs", _MAX_TURNS, elapsed)
    return "I wasn't able to complete that after several steps. Could you rephrase or try again?"
