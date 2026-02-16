"""Chat agent — LangGraph graph for interactive user conversations.

Intent detection uses LLM classification for robust intent matching
and TODO normalization. Graph nodes are pure — DB writes happen in
the WebSocket handler.
"""

import json
import logging
from enum import StrEnum
from typing import TypedDict

from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)

_VALID_INTENTS = frozenset({"todo_capture", "todo_update", "memory_write", "prioritize", "chat"})

_CLASSIFY_SYSTEM_PROMPT = """\
You are an intent classifier for a personal assistant. Given a user message, \
return a JSON object with exactly two keys:
{"intent": "<intent>", "extracted_content": "<content>"}

Intents:
- "todo_capture": User wants to add a task, reminder, or TODO. \
Set extracted_content to a plain string: the task rephrased as a concise action \
starting with a verb (e.g., "Pay the condo fee", "Buy groceries").
- "todo_update": User wants to change the status of an existing TODO \
(e.g., "mark task 3 as blocked", "start working on groceries", "defer the report"). \
Return extracted_content as JSON: {"identifier": "<id or title>", "target_status": "<status>"}. \
Valid statuses: open, in_progress, blocked, complete, deferred.
- "memory_write": User wants you to remember a fact or preference. Extract the fact.
- "prioritize": User is asking what to work on or to see their priorities. \
Set extracted_content to "".
- "chat": General conversation, questions, or anything else. \
Set extracted_content to "".

Return ONLY valid JSON, no other text."""


class Intent(StrEnum):
    TODO_CAPTURE = "todo_capture"
    TODO_UPDATE = "todo_update"
    MEMORY_WRITE = "memory_write"
    PRIORITIZE = "prioritize"
    CHAT = "chat"


class ChatState(TypedDict, total=False):
    user_message: str
    intent: str
    extracted_content: str
    todo_identifier: str
    target_status: str
    response: str
    is_sensitive: bool


# --- Graph nodes ---


async def classify_node(state: ChatState) -> ChatState:
    """Classify the user message via LLM and detect intent."""
    from istari.llm.router import completion
    from istari.tools.classifier.rules import classify

    msg = state["user_message"]
    classification = classify(msg)

    intent = Intent.CHAT.value
    extracted = ""

    try:
        llm_result = await completion(
            "classification",
            [
                {"role": "system", "content": _CLASSIFY_SYSTEM_PROMPT},
                {"role": "user", "content": msg},
            ],
            sensitive=classification.is_sensitive,
        )
        content = llm_result.choices[0].message.content or ""
        parsed = json.loads(content)
        raw_intent = parsed.get("intent", "chat")
        raw_extracted = parsed.get("extracted_content", "")
        if not isinstance(raw_extracted, str):
            raw_extracted = json.dumps(raw_extracted) if raw_extracted is not None else ""
        if raw_intent in _VALID_INTENTS:
            intent = raw_intent
            extracted = raw_extracted.strip()
        else:
            logger.warning("LLM returned unknown intent %r, falling back to chat", raw_intent)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Failed to parse LLM classification response: %s", exc)
    except Exception:
        logger.exception("LLM classification call failed")

    updates: ChatState = {
        **state,
        "intent": intent,
        "extracted_content": extracted,
        "is_sensitive": classification.is_sensitive,
    }

    if intent == Intent.TODO_UPDATE.value:
        try:
            payload = json.loads(extracted) if extracted else {}
            updates["todo_identifier"] = str(payload.get("identifier", ""))
            updates["target_status"] = str(payload.get("target_status", ""))
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse todo_update extracted_content, falling back to chat")
            updates["intent"] = Intent.CHAT.value

    return updates


def todo_capture_node(state: ChatState) -> ChatState:
    """Produce a TODO capture acknowledgment (no DB write — handler does that)."""
    title = state.get("extracted_content", "")
    return {**state, "response": f'Got it! Added TODO: "{title}"'}


def memory_write_node(state: ChatState) -> ChatState:
    """Produce a memory write acknowledgment (no DB write — handler does that)."""
    return {**state, "response": "Noted. I'll remember that."}


def prioritize_node(state: ChatState) -> ChatState:
    """Signal that we need prioritized TODOs (handler fetches from DB)."""
    return {**state, "response": "__PRIORITIZE__"}


def todo_update_node(state: ChatState) -> ChatState:
    """Signal a TODO status update (handler does DB write)."""
    identifier = state.get("todo_identifier", "")
    target = state.get("target_status", "")
    return {**state, "response": f"__TODO_UPDATE__|{identifier}|{target}"}


def chat_respond_node(state: ChatState) -> ChatState:
    """Signal that an LLM call is needed (handler calls the LLM)."""
    return {**state, "response": "__LLM_CALL__"}


def _route_intent(state: ChatState) -> str:
    """Route to the appropriate node based on detected intent."""
    intent = state.get("intent", Intent.CHAT.value)
    if intent == Intent.TODO_CAPTURE.value:
        return "todo_capture"
    if intent == Intent.TODO_UPDATE.value:
        return "todo_update"
    if intent == Intent.MEMORY_WRITE.value:
        return "memory_write"
    if intent == Intent.PRIORITIZE.value:
        return "prioritize"
    return "chat_respond"


# --- Build graph ---


def build_chat_graph() -> StateGraph:
    """Build and compile the chat agent graph."""
    graph = StateGraph(ChatState)

    graph.add_node("classify", classify_node)
    graph.add_node("todo_capture", todo_capture_node)
    graph.add_node("todo_update", todo_update_node)
    graph.add_node("memory_write", memory_write_node)
    graph.add_node("prioritize", prioritize_node)
    graph.add_node("chat_respond", chat_respond_node)

    graph.set_entry_point("classify")

    graph.add_conditional_edges(
        "classify",
        _route_intent,
        {
            "todo_capture": "todo_capture",
            "todo_update": "todo_update",
            "memory_write": "memory_write",
            "prioritize": "prioritize",
            "chat_respond": "chat_respond",
        },
    )

    graph.add_edge("todo_capture", END)
    graph.add_edge("todo_update", END)
    graph.add_edge("memory_write", END)
    graph.add_edge("prioritize", END)
    graph.add_edge("chat_respond", END)

    return graph.compile()


chat_graph = build_chat_graph()
