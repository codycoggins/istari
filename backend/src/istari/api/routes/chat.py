"""Chat/conversation endpoints (WebSocket + REST)."""

import datetime
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from istari.agents.chat import Intent, chat_graph
from istari.db.session import async_session_factory
from istari.tools.memory.store import MemoryStore
from istari.tools.todo.manager import TodoManager

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

            result = await chat_graph.ainvoke({"user_message": user_message})

            intent = result.get("intent", Intent.CHAT.value)
            response_text = result.get("response", "")
            extracted = result.get("extracted_content", "")
            is_sensitive = result.get("is_sensitive", False)

            todo_created = False
            memory_created = False

            async with async_session_factory() as session:
                if intent == Intent.TODO_CAPTURE.value and extracted:
                    mgr = TodoManager(session)
                    await mgr.create(title=extracted, source="chat")
                    await session.commit()
                    todo_created = True

                elif intent == Intent.MEMORY_WRITE.value and extracted:
                    store = MemoryStore(session)
                    await store.store(content=extracted, source="chat")
                    await session.commit()
                    memory_created = True

                elif intent == Intent.PRIORITIZE.value:
                    mgr = TodoManager(session)
                    todos = await mgr.get_prioritized(limit=3)
                    if todos:
                        lines = ["Here's what I'd focus on:"]
                        for i, t in enumerate(todos, 1):
                            line = f"{i}. {t.title}"
                            if t.priority is not None:
                                line += f" (priority {t.priority})"
                            lines.append(line)
                        response_text = "\n".join(lines)
                    else:
                        response_text = "You don't have any active TODOs right now."

                elif response_text == "__LLM_CALL__":
                    try:
                        from istari.llm.router import completion

                        llm_messages = [
                            {
                                "role": "system",
                                "content": "You are Istari, a helpful AI assistant.",
                            },
                            *history,
                        ]
                        llm_result = await completion(
                            "chat_response",
                            llm_messages,
                            sensitive=is_sensitive,
                        )
                        response_text = llm_result.choices[0].message.content or ""
                    except Exception:
                        response_text = (
                            "I'm having trouble connecting to the language model. "
                            "Try again in a moment."
                        )

            history.append({"role": "assistant", "content": response_text})

            await ws.send_json({
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": response_text,
                "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "todo_created": todo_created,
                "memory_created": memory_created,
            })

    except WebSocketDisconnect:
        pass
