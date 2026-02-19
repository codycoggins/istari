"""Proactive agent — LangGraph graph for background/scheduled tasks.

Runs Gmail digest, TODO staleness checks, and morning digest aggregation.
Graph nodes are pure — DB writes happen in the worker job callers.
"""

import logging
from dataclasses import asdict
from typing import TypedDict

from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)


class ProactiveState(TypedDict, total=False):
    task_type: str  # "gmail_digest", "morning_digest", "staleness_only"
    gmail_token_path: str
    gmail_max_results: int
    stale_todo_days: int
    db_session: object  # AsyncSession — passed through, used by nodes
    emails: list[dict]
    stale_todos: list[dict]
    digest_text: str
    notifications: list[dict]


# --- Graph nodes ---


async def scan_gmail_node(state: ProactiveState) -> ProactiveState:
    """Scan Gmail for unread messages."""
    from istari.tools.gmail.reader import GmailReader

    token_path = state.get("gmail_token_path", "gmail_token.json")
    max_results = state.get("gmail_max_results", 20)

    try:
        reader = GmailReader(token_path)
        emails = await reader.list_unread(max_results=max_results)
        email_dicts = [asdict(e) for e in emails]
    except FileNotFoundError:
        logger.warning("Gmail token not found — skipping email scan")
        email_dicts = []
    except Exception:
        logger.exception("Gmail scan failed")
        email_dicts = []

    return {**state, "emails": email_dicts}


async def check_staleness_node(state: ProactiveState) -> ProactiveState:
    """Check for stale TODOs."""
    from istari.tools.todo.manager import TodoManager

    session = state.get("db_session")
    days = state.get("stale_todo_days", 3)
    stale: list[dict] = []

    if session is not None:
        try:
            mgr = TodoManager(session)  # type: ignore[arg-type]
            todos = await mgr.get_stale(days=days)
            stale = [
                {"id": t.id, "title": t.title, "status": t.status.value,
                 "updated_at": str(t.updated_at)}
                for t in todos
            ]
        except Exception:
            logger.exception("Staleness check failed")

    return {**state, "stale_todos": stale}


async def summarize_node(state: ProactiveState) -> ProactiveState:
    """Produce a digest summary from emails and/or stale TODOs via LLM."""
    from istari.llm.router import completion

    emails = state.get("emails", [])
    stale = state.get("stale_todos", [])

    if not emails and not stale:
        return {**state, "digest_text": "No new emails or stale TODOs to report."}

    parts: list[str] = []
    if emails:
        email_lines = [f"- {e['subject']} (from {e['sender']}): {e['snippet']}" for e in emails]
        parts.append("Unread emails:\n" + "\n".join(email_lines))
    if stale:
        todo_lines = [
            f"- [{t['status']}] {t['title']} (last updated {t['updated_at']})"
            for t in stale
        ]
        parts.append("Stale TODOs:\n" + "\n".join(todo_lines))

    user_content = "\n\n".join(parts)

    try:
        result = await completion(
            "digest_summary",
            [
                {
                    "role": "system",
                    "content": (
                        "You are a concise personal assistant. "
                        "Summarize the following items into an actionable digest. "
                        "Group by urgency. Be brief - 2-5 bullet points max. "
                        "For emails, note which need a reply. "
                        "For stale TODOs, suggest next actions."
                    ),
                },
                {"role": "user", "content": user_content},
            ],
        )
        digest_text = result.choices[0].message.content or ""
    except Exception:
        logger.exception("LLM summarization failed, using raw content")
        digest_text = user_content

    return {**state, "digest_text": digest_text}


def queue_notifications_node(state: ProactiveState) -> ProactiveState:
    """Prepare notification dicts for the caller to persist."""
    digest_text = state.get("digest_text", "")
    task_type = state.get("task_type", "unknown")

    if not digest_text or digest_text == "No new emails or stale TODOs to report.":
        return {**state, "notifications": []}

    source_map = {
        "gmail_digest": "gmail_digest",
        "morning_digest": "morning_digest",
        "staleness_only": "todo_staleness",
    }
    notif_type = source_map.get(task_type, "digest")

    notifications = [{"type": notif_type, "content": digest_text}]
    return {**state, "notifications": notifications}


# --- Routing ---


def _route_task(state: ProactiveState) -> str:
    task_type = state.get("task_type", "")
    if task_type == "gmail_digest":
        return "scan_gmail"
    if task_type == "morning_digest":
        return "scan_gmail"  # morning digest starts with gmail, then staleness
    if task_type == "staleness_only":
        return "check_staleness"
    logger.warning("Unknown proactive task_type %r, defaulting to scan_gmail", task_type)
    return "scan_gmail"


def _after_gmail(state: ProactiveState) -> str:
    """After gmail scan, morning_digest also checks staleness; gmail_digest goes to summarize."""
    if state.get("task_type") == "morning_digest":
        return "check_staleness"
    return "summarize"


# --- Build graph ---


def build_proactive_graph() -> StateGraph:
    graph = StateGraph(ProactiveState)

    graph.add_node("scan_gmail", scan_gmail_node)
    graph.add_node("check_staleness", check_staleness_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("queue_notifications", queue_notifications_node)

    graph.set_entry_point("route")
    graph.add_node("route", lambda state: state)  # pass-through for routing

    graph.add_conditional_edges(
        "route",
        _route_task,
        {
            "scan_gmail": "scan_gmail",
            "check_staleness": "check_staleness",
        },
    )

    graph.add_conditional_edges(
        "scan_gmail",
        _after_gmail,
        {
            "check_staleness": "check_staleness",
            "summarize": "summarize",
        },
    )

    graph.add_edge("check_staleness", "summarize")
    graph.add_edge("summarize", "queue_notifications")
    graph.add_edge("queue_notifications", END)

    return graph.compile()


proactive_graph = build_proactive_graph()
