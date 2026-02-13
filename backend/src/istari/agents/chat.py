"""Chat agent — LangGraph graph for interactive user conversations.

Intent detection is regex-based (Phase 1): fast, free, deterministic.
Graph nodes are pure — DB writes happen in the WebSocket handler.
"""

import re
from enum import StrEnum
from typing import TypedDict

from langgraph.graph import END, StateGraph


class Intent(StrEnum):
    TODO_CAPTURE = "todo_capture"
    MEMORY_WRITE = "memory_write"
    PRIORITIZE = "prioritize"
    CHAT = "chat"


class ChatState(TypedDict, total=False):
    user_message: str
    intent: str
    extracted_content: str
    response: str
    is_sensitive: bool


# --- Intent detection patterns ---

_TODO_PATTERNS = [
    re.compile(r"(?:^|\s)(?:TODO|todo)[\s:]+(.+)", re.IGNORECASE),
    re.compile(r"(?:^|\s)remind\s+me\s+to\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:^|\s)(?:add|create)\s+(?:a\s+)?(?:todo|task)[\s:]+(.+)", re.IGNORECASE),
    re.compile(r"(?:^|\s)(?:i\s+)?need\s+to\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:^|\s)don'?t\s+(?:let\s+me\s+)?forget\s+to\s+(.+)", re.IGNORECASE),
]

_MEMORY_PATTERNS = [
    re.compile(r"(?:^|\s)remember\s+that\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:^|\s)(?:note|keep\s+in\s+mind)\s+that\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:^|\s)(?:i\s+)?(?:prefer|like|hate|dislike)\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:^|\s)(?:fyi|for\s+your\s+info(?:rmation)?)\s*[,:]\s*(.+)", re.IGNORECASE),
]

_PRIORITIZE_PATTERNS = [
    re.compile(r"what\s+should\s+i\s+(?:work\s+on|do|focus\s+on)", re.IGNORECASE),
    re.compile(
        r"(?:show|list|get)\s+(?:my\s+)?(?:priorities|top\s+(?:todos|tasks))", re.IGNORECASE
    ),
    re.compile(r"prioriti[sz]e", re.IGNORECASE),
]


def _detect_intent(text: str) -> tuple[Intent, str]:
    """Detect user intent and extract relevant content."""
    for pattern in _TODO_PATTERNS:
        match = pattern.search(text)
        if match:
            return Intent.TODO_CAPTURE, match.group(1).strip()

    for pattern in _MEMORY_PATTERNS:
        match = pattern.search(text)
        if match:
            return Intent.MEMORY_WRITE, match.group(1).strip()

    for pattern in _PRIORITIZE_PATTERNS:
        if pattern.search(text):
            return Intent.PRIORITIZE, ""

    return Intent.CHAT, ""


# --- Graph nodes ---


def classify_node(state: ChatState) -> ChatState:
    """Classify the user message and detect intent."""
    from istari.tools.classifier.rules import classify

    msg = state["user_message"]
    classification = classify(msg)
    intent, extracted = _detect_intent(msg)
    return {
        **state,
        "intent": intent.value,
        "extracted_content": extracted,
        "is_sensitive": classification.is_sensitive,
    }


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


def chat_respond_node(state: ChatState) -> ChatState:
    """Signal that an LLM call is needed (handler calls the LLM)."""
    return {**state, "response": "__LLM_CALL__"}


def _route_intent(state: ChatState) -> str:
    """Route to the appropriate node based on detected intent."""
    intent = state.get("intent", Intent.CHAT.value)
    if intent == Intent.TODO_CAPTURE.value:
        return "todo_capture"
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
    graph.add_node("memory_write", memory_write_node)
    graph.add_node("prioritize", prioritize_node)
    graph.add_node("chat_respond", chat_respond_node)

    graph.set_entry_point("classify")

    graph.add_conditional_edges(
        "classify",
        _route_intent,
        {
            "todo_capture": "todo_capture",
            "memory_write": "memory_write",
            "prioritize": "prioritize",
            "chat_respond": "chat_respond",
        },
    )

    graph.add_edge("todo_capture", END)
    graph.add_edge("memory_write", END)
    graph.add_edge("prioritize", END)
    graph.add_edge("chat_respond", END)

    return graph.compile()


chat_graph = build_chat_graph()
