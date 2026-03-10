"""Gather contextual information for a single todo item.

Runs a mini-agent with a focused subset of tools (memory, Gmail, Calendar,
web search) and a targeted system prompt.  The agent decides whether a web
search is genuinely helpful and returns a concise markdown summary.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are gathering context to help the user work on a specific task.

Steps:
1. Search memory for anything relevant to the task title.
2. Search Gmail for related emails or threads.
3. Search the calendar for related events or meetings.
4. Only use web_search if the task genuinely requires current external
   information — e.g. a specific product, place, service, or current event.
   Do NOT web-search generic personal tasks like "call dentist" or "pay bills".

Return a markdown summary, organised by source.
Include hyperlinks to mail, calendar, or web items when available.
Omit any source that returned nothing useful.
Use short bullet points. If nothing relevant was found anywhere, say so briefly.
"""


async def get_todo_context(title: str, session: "AsyncSession") -> str:
    """Return a markdown context summary for a todo item title."""
    from istari.agents.chat import run_agent
    from istari.agents.tools.base import AgentContext
    from istari.agents.tools.calendar import make_calendar_tools
    from istari.agents.tools.gmail import make_gmail_tools
    from istari.agents.tools.memory import make_memory_tools
    from istari.agents.tools.web import make_web_search_tools

    context = AgentContext()
    tools = [
        *make_memory_tools(session, context),
        *make_gmail_tools(),
        *make_calendar_tools(),
        *make_web_search_tools(),
    ]

    logger.info("todo_context | title=%r", title)
    return await run_agent(
        f'Gather context for this task: "{title}"',
        [],
        tools,
        system_prompt=_SYSTEM_PROMPT,
    )
