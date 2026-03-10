"""Chat/conversation endpoints (WebSocket + REST)."""

import asyncio
import contextlib
import datetime
import time
import uuid
from collections import deque

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from istari.agents.chat import build_system_prompt, build_tools, run_agent
from istari.agents.memory_extractor import extract_and_store
from istari.agents.tools.base import AgentContext
from istari.api.auth import COOKIE_NAME, verify_token
from istari.config.settings import settings
from istari.db.session import async_session_factory
from istari.tools.conversation.store import ConversationStore

router = APIRouter(prefix="/chat", tags=["chat"])

_WS_RATE_LIMIT = 20    # max messages per window
_WS_RATE_WINDOW = 60.0  # sliding window in seconds


class _RateLimiter:
    """Per-connection sliding-window rate limiter.

    Tracks message timestamps in a deque.  ``is_allowed()`` evicts entries
    older than the window, then returns False (and does NOT record the attempt)
    if the limit is already reached, or True (and records the timestamp) if
    the message is within budget.
    """

    def __init__(self, limit: int, window: float) -> None:
        self._limit = limit
        self._window = window
        self._timestamps: deque[float] = deque()

    def is_allowed(self) -> bool:
        now = time.monotonic()
        while self._timestamps and now - self._timestamps[0] > self._window:
            self._timestamps.popleft()
        if len(self._timestamps) >= self._limit:
            return False
        self._timestamps.append(now)
        return True


@router.get("/")
async def get_conversations() -> dict[str, list[object]]:
    return {"conversations": []}


@router.websocket("/ws")
async def chat_ws(ws: WebSocket) -> None:
    # Authenticate via session cookie before accepting the connection.
    # Close code 4401 signals the frontend to show the login screen.
    if settings.app_secret_key:
        token = ws.cookies.get(COOKIE_NAME, "")
        if not verify_token(token, settings.app_secret_key):
            await ws.accept()
            await ws.close(code=4401)
            return

    await ws.accept()

    # Load history once at connection time
    async with async_session_factory() as session:
        history = await ConversationStore(session).load_history()

    rate_limiter = _RateLimiter(limit=_WS_RATE_LIMIT, window=_WS_RATE_WINDOW)

    try:
        while True:
            data = await ws.receive_json()
            user_message = data.get("message", "").strip()
            if not user_message:
                continue

            if not rate_limiter.is_allowed():
                await ws.send_json({
                    "type": "response",
                    "id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": (
                        f"You've sent {_WS_RATE_LIMIT} messages in the last minute. "
                        "Please wait a moment before continuing."
                    ),
                    "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
                    "todo_created": False,
                    "todo_updated": False,
                    "memory_created": False,
                })
                continue

            context = AgentContext()
            mcp_tools = getattr(ws.app.state, "mcp_tools", [])

            async def _send_status(text: str) -> None:
                with contextlib.suppress(Exception):
                    await ws.send_json({"type": "status", "content": text})

            async with async_session_factory() as session:
                tools = build_tools(session, context, mcp_tools=mcp_tools)
                system_prompt = await build_system_prompt(
                    session, settings.user_name, user_message=user_message
                )
                response_text = await run_agent(
                    user_message,
                    history,
                    tools,
                    system_prompt=system_prompt,
                    context=context,
                    status_callback=_send_status,
                )

            if context.tool_errors:
                error_lines = "\n".join(f"- {e}" for e in context.tool_errors)
                response_text += f"\n\n⚠️ Some actions couldn't complete:\n{error_lines}"

            async with async_session_factory() as session:
                await ConversationStore(session).save_turn(user_message, response_text)
                await session.commit()

            # Update in-memory history for the rest of this connection
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": response_text})

            # Fire-and-forget: extract memorable facts in the background.
            asyncio.create_task(  # noqa: RUF006
                extract_and_store(user_message, response_text, async_session_factory)
            )

            await ws.send_json({
                "type": "response",
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": response_text,
                "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "todo_created": context.todo_created,
                "todo_updated": context.todo_updated,
                "memory_created": context.memory_created,
            })

    except WebSocketDisconnect:
        pass
