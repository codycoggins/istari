"""Chat/conversation endpoints (WebSocket + REST)."""

import datetime
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from istari.agents.chat import build_tools, run_agent
from istari.agents.tools.base import AgentContext
from istari.config.settings import settings
from istari.db.session import async_session_factory

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/")
async def get_conversations() -> dict:
    return {"conversations": []}


@router.websocket("/ws")
async def chat_ws(ws: WebSocket):
    await ws.accept()
    history: list[dict[str, str]] = []

    try:
        while True:
            data = await ws.receive_json()
            user_message = data.get("message", "").strip()
            if not user_message:
                continue

            history.append({"role": "user", "content": user_message})

            context = AgentContext()

            async with async_session_factory() as session:
                tools = build_tools(session, context)
                response_text = await run_agent(
                    user_message,
                    history[:-1],  # history before this message
                    tools,
                    user_name=settings.user_name,
                )

            history.append({"role": "assistant", "content": response_text})

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
