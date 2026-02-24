"""Chat/conversation endpoints (WebSocket + REST)."""

import asyncio
import datetime
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from istari.agents.chat import build_system_prompt, build_tools, run_agent
from istari.agents.memory_extractor import extract_and_store
from istari.agents.tools.base import AgentContext
from istari.config.settings import settings
from istari.db.session import async_session_factory
from istari.tools.conversation.store import ConversationStore

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/")
async def get_conversations() -> dict[str, list[object]]:
    return {"conversations": []}


@router.websocket("/ws")
async def chat_ws(ws: WebSocket) -> None:
    await ws.accept()

    # Load history once at connection time
    async with async_session_factory() as session:
        history = await ConversationStore(session).load_history()

    try:
        while True:
            data = await ws.receive_json()
            user_message = data.get("message", "").strip()
            if not user_message:
                continue

            context = AgentContext()

            async with async_session_factory() as session:
                tools = build_tools(session, context)
                system_prompt = await build_system_prompt(session, settings.user_name)
                response_text = await run_agent(
                    user_message,
                    history,
                    tools,
                    system_prompt=system_prompt,
                )
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
