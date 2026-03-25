"""Chat agent — ReAct tool-calling loop for interactive user conversations.

Architecture: the LLM receives a set of tools and reasons across multiple turns:
  1. User message arrives
  2. LLM decides which tool(s) to call (or responds directly)
  3. Tools execute and return results
  4. LLM sees results, may call more tools or produce a final response
  5. Loop continues until a final text response or max_turns is reached

System prompt is assembled fresh on each turn from three sources (in order):
  1. memory/SOUL.md  — agent personality (editable, checked into git)
  2. memory/USER.md  — user profile (editable, gitignored)
  3. Stored memories — semantically relevant to the current message (via pgvector cosine
     similarity), falling back to newest-N when no message context or embeddings unavailable

Tools are bound to the current DB session at WebSocket connect time via closures,
so the agent has no direct DB access — all persistence goes through tool functions.
"""

import json
import logging
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall

from istari.agents.tools.base import AgentContext, AgentTool

logger = logging.getLogger(__name__)


def _format_tool_status(tool_name: str, args: dict[str, Any]) -> str:
    """Return a human-readable status string for a tool call."""
    match tool_name:
        case "check_email":
            q = args.get("query")
            return f"Searching Gmail for '{q}'..." if q else "Checking Gmail for unread messages..."
        case "check_calendar":
            q = args.get("query")
            return f"Searching calendar for '{q}'..." if q else "Checking your calendar..."
        case "create_todos":
            titles = args.get("titles", [])
            n = len(titles)
            return f"Creating task: '{titles[0][:40]}'..." if n == 1 else f"Creating {n} tasks..."
        case "list_todos":
            f = args.get("filter", "open")
            label = {"open": "open", "all": "all", "complete": "completed"}.get(f, f)
            return f"Looking at your {label} task list..."
        case "update_todo_status":
            status = args.get("status", "")
            return f"Updating task status to '{status}'..."
        case "update_todo_priority":
            return "Updating task priority..."
        case "get_priorities":
            return "Getting your priorities..."
        case "set_today_focus":
            return "Setting today's focus tasks..."
        case "get_today_focus":
            return "Getting today's focus tasks..."
        case "remember":
            fact = args.get("fact", "")
            return f"Saving to memory: '{fact[:40]}'..." if fact else "Saving to memory..."
        case "search_memory":
            q = args.get("query", "")
            return f"Searching memory for '{q}'..." if q else "Searching memory..."
        case "read_file":
            path = args.get("path", "")
            return f"Reading file: {path}..." if path else "Reading file..."
        case "search_files":
            q = args.get("query", "")
            d = args.get("directory", "")
            if d:
                return f"Searching files in {d} for '{q}'..."
            return f"Searching files for '{q}'..." if q else "Searching files..."
        case _:
            label = tool_name.replace("_", " ").title()
            return f"Running {label}..."

# Keywords that indicate the user is requesting a mutation (create/update/delete)
_MUTATION_VERBS = (
    "add", "create", "new todo", "new task", "mark", "update", "complete",
    "finish", "done", "set", "remove", "delete", "remember", "save",
)


def _looks_like_mutation(user_message: str) -> bool:
    """Return True if the message appears to request a data-modifying action."""
    lower = user_message.lower()
    return any(verb in lower for verb in _MUTATION_VERBS)


_MAX_TURNS = 8
_MAX_PROMPT_MEMORIES = 20

# In dev (editable install): .../src/istari/agents/chat.py → parents[4] = project root
# In Docker (regular install): lives under site-packages → fall back to WORKDIR (/app)
_PROJECT_ROOT = (
    Path.cwd()
    if "site-packages" in str(Path(__file__).resolve())
    else Path(__file__).resolve().parents[4]
)
_MEMORY_DIR = _PROJECT_ROOT / "memory"

_FALLBACK_SOUL = """\
You are Istari, a personal AI assistant.
You help the user manage their TODOs, memories, email, calendar, and local files.
Be concise, action-oriented, and use the available tools when relevant.

IMPORTANT: Never claim to have performed any action without first calling the
appropriate tool. If you say "I've added that task" or "Done!", the tool call
must have happened in this same turn. Do not confirm mutations based on prior
conversation history alone — always invoke the tool.
"""


def _read_memory_file(filename: str) -> str:
    """Read a file from memory/. Returns empty string if missing or unreadable."""
    try:
        return (_MEMORY_DIR / filename).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


async def build_system_prompt(
    session: "AsyncSession",
    user_name: str = "",
    user_message: str = "",
) -> str:
    """Assemble the full system prompt from SOUL.md, USER.md, and stored memories.

    Injection order:
      1. SOUL.md  (agent personality — falls back to minimal default if missing)
      2. USER.md  (user profile — optional; falls back to user_name setting)
      3. Relevant memories: semantic search on user_message when provided (pgvector cosine),
         falling back to newest-N when no message or embeddings unavailable
    """
    from istari.tools.memory.store import MemoryStore

    soul = _read_memory_file("SOUL.md") or _FALLBACK_SOUL
    user_profile = _read_memory_file("USER.md")

    store = MemoryStore(session)
    if user_message:
        memories = await store.search(user_message)
        if not memories:
            memories = await store.list_explicit()
    else:
        memories = await store.list_explicit()

    parts: list[str] = [soul]

    if user_profile:
        parts.append(f"## User Profile\n\n{user_profile}")
    elif user_name:
        parts.append(f"The user's name is {user_name}.")

    if memories:
        mem_lines = [f"- {m.content}" for m in memories[:_MAX_PROMPT_MEMORIES]]
        parts.append("## What you know about this user\n\n" + "\n".join(mem_lines))

    return "\n\n---\n\n".join(parts)


def build_tools(
    session: "AsyncSession",
    context: AgentContext,
    mcp_tools: list[AgentTool] | None = None,
) -> list[AgentTool]:
    """Assemble all agent tools bound to this session.

    mcp_tools: optional list of tools loaded from external MCP servers at startup;
    they are appended after the built-in tools so built-ins always take precedence.
    """
    from istari.agents.tools.calendar import make_calendar_tools
    from istari.agents.tools.filesystem import make_filesystem_tools
    from istari.agents.tools.gmail import make_gmail_tools
    from istari.agents.tools.memory import make_memory_tools
    from istari.agents.tools.projects import make_project_tools
    from istari.agents.tools.todo import make_todo_tools
    from istari.agents.tools.web import make_web_search_tools

    tools: list[AgentTool] = [
        *make_todo_tools(session, context),
        *make_project_tools(session, context),
        *make_memory_tools(session, context),
        *make_gmail_tools(),
        *make_calendar_tools(),
        *make_filesystem_tools(),
        *make_web_search_tools(),
    ]
    if mcp_tools:
        tools.extend(mcp_tools)
    return tools


async def run_agent(
    user_message: str,
    history: list[dict[str, Any]],
    tools: list[AgentTool],
    *,
    system_prompt: str,
    context: AgentContext | None = None,
    status_callback: Callable[[str], Awaitable[None]] | None = None,
) -> str:
    """Run the ReAct agent loop and return the final response text."""
    from istari.llm.router import completion

    tool_map = {t.name: t for t in tools}
    tool_schemas = [t.to_openai_schema() for t in tools]

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message},
    ]

    agent_start = time.monotonic()
    logger.info("Agent start | user=%r | tools=%s", user_message[:80], [t.name for t in tools])
    context_has_tool_calls = False

    for turn in range(_MAX_TURNS):
        logger.debug("Agent turn %d/%d | %d msgs", turn + 1, _MAX_TURNS, len(messages))

        if status_callback is not None:
            logger.debug("Status | Thinking...")
            await status_callback("Thinking...")

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

        # No tool calls — check if the response is a false mutation claim
        if not getattr(msg, "tool_calls", None):
            content = msg.content or ""
            if turn == 0 and _looks_like_mutation(user_message) and not context_has_tool_calls:
                logger.warning(
                    "Agent turn 1 claimed mutation without tool call — injecting correction"
                )
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": (
                        "You described performing an action but didn't call any tools. "
                        "Please call the appropriate tool now to actually perform the action."
                    ),
                })
                continue
            elapsed = time.monotonic() - agent_start
            logger.info("Agent done | turns=%d | %.2fs", turn + 1, elapsed)
            return content

        # Add assistant message with tool calls to context
        # cast: in practice tool_choice="auto" only returns function tool calls
        tool_calls = cast(list[ChatCompletionMessageToolCall], msg.tool_calls or [])
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
                for tc in tool_calls
            ],
        })

        # Execute each tool call and append results
        context_has_tool_calls = True
        for tc in tool_calls:
            tool_name = tc.function.name
            tool = tool_map.get(tool_name)
            try:
                args: dict[str, Any] = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            logger.info("Tool start | %-24s | %s", tool_name, args)
            if status_callback is not None:
                status_text = _format_tool_status(tool_name, args)
                logger.debug("Status    | %s", status_text)
                await status_callback(status_text)
            logger.info("Tool args | %s | %s", tool_name, tc.function.arguments)

            if tool is None:
                logger.warning("Tool called but not found: %r", tool_name)
                tool_result = f"Unknown tool: {tool_name}"
            else:
                t0 = time.monotonic()
                try:
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
                    tool_result = f"[TOOL_FAILED:{tool_name}] {type(exc).__name__}: {exc}"
                    if context is not None:
                        context.tool_errors.append(f"{tool_name}: {exc}")

            logger.info("Tool result | %s | %r", tool_name, tool_result[:200])
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_result,
            })

    elapsed = time.monotonic() - agent_start
    logger.warning("Agent max turns reached | %d turns | %.2fs", _MAX_TURNS, elapsed)
    return "I wasn't able to complete that after several steps. Could you rephrase or try again?"
