"""Chat/conversation endpoints (WebSocket + REST)."""

import contextlib
import datetime
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from istari.agents.chat import Intent, chat_graph
from istari.config.settings import settings
from istari.db.session import async_session_factory
from istari.models.todo import Todo, TodoStatus
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
            todo_updated = False
            memory_created = False

            async with async_session_factory() as session:
                if intent == Intent.TODO_CAPTURE.value and extracted:
                    mgr = TodoManager(session)
                    await mgr.create(title=extracted, source="chat")
                    await session.commit()
                    todo_created = True

                elif intent == Intent.TODO_UPDATE.value:
                    identifier = result.get("todo_identifier", "")
                    target_status_str = result.get("target_status", "")
                    try:
                        new_status = TodoStatus(target_status_str)
                    except ValueError:
                        response_text = (
                            f"I don't recognize the status \"{target_status_str}\". "
                            f"Valid statuses: {', '.join(s.value for s in TodoStatus)}."
                        )
                    else:
                        mgr = TodoManager(session)
                        todo = None
                        with contextlib.suppress(ValueError, TypeError):
                            todo = await mgr.get(int(identifier))
                        if todo is None:
                            stmt = select(Todo).where(
                                Todo.title.ilike(f"%{identifier}%")
                            ).limit(1)
                            row = await session.execute(stmt)
                            todo = row.scalars().first()
                        if todo is None:
                            response_text = f"I couldn't find a TODO matching \"{identifier}\"."
                        else:
                            await mgr.set_status(todo.id, new_status)
                            await session.commit()
                            todo_updated = True
                            response_text = (
                                f"Updated \"{todo.title}\" to {new_status.value}."
                            )

                elif intent == Intent.GMAIL_SCAN.value:
                    query = extracted or ""
                    try:
                        from istari.tools.gmail.reader import GmailReader

                        reader = GmailReader(settings.gmail_token_path)
                        if query:
                            emails = await reader.search(query, max_results=10)
                        else:
                            emails = await reader.list_unread(max_results=10)

                        if not emails:
                            if not query:
                                response_text = "No unread emails found."
                            else:
                                response_text = f'No emails matching "{query}".'
                        else:
                            from istari.llm.router import completion

                            email_lines = [
                                f"- {e.subject} (from {e.sender}): {e.snippet}"
                                for e in emails
                            ]
                            summary_prompt = "\n".join(email_lines)
                            llm_result = await completion(
                                "gmail_summary",
                                [
                                    {
                                        "role": "system",
                                        "content": (
                                            "Summarize these emails concisely for the user. "
                                            "Note which ones need a reply or action."
                                        ),
                                    },
                                    {"role": "user", "content": summary_prompt},
                                ],
                            )
                            response_text = llm_result.choices[0].message.content or summary_prompt
                    except FileNotFoundError:
                        response_text = (
                            "Gmail isn't set up yet. Run `python scripts/setup_gmail.py` "
                            "to connect your Gmail account."
                        )
                    except Exception:
                        response_text = "I had trouble checking your email. Try again in a moment."

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
                "todo_updated": todo_updated,
                "memory_created": memory_created,
            })

    except WebSocketDisconnect:
        pass
