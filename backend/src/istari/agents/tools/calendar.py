"""Calendar agent tools — read and search Google Calendar events."""

import logging

from .base import AgentTool

logger = logging.getLogger(__name__)


def make_calendar_tools() -> list[AgentTool]:
    """Return Calendar tools. No session needed — uses OAuth token from settings."""

    async def check_calendar(query: str = "", days: int = 7) -> str:
        from istari.config.settings import settings
        from istari.tools.calendar.reader import CalendarReader

        try:
            reader = CalendarReader(settings.calendar_token_path)
            max_r = settings.calendar_max_results
            if query:
                events = await reader.search(query, max_results=max_r)
            else:
                events = await reader.list_upcoming(days=days, max_results=max_r)
        except FileNotFoundError:
            return (
                "Google Calendar isn't connected yet. "
                "Run `python scripts/setup_calendar.py` to link your calendar."
            )
        except Exception:
            logger.exception("Calendar tool error")
            return "Couldn't reach Google Calendar. Try again in a moment."

        if not events:
            if query:
                return f'No calendar events matching "{query}".'
            return f"No upcoming events in the next {days} days."

        lines = []
        for e in events:
            start = e.start.isoformat() if e.start else "?"
            loc = f" @ {e.location}" if e.location else ""
            lines.append(f"- {e.summary} ({start}{loc})")
        return f"Found {len(events)} event(s):\n" + "\n".join(lines)

    return [
        AgentTool(
            name="check_calendar",
            description=(
                "Check the user's Google Calendar. With no query, returns upcoming events "
                "for the next `days` days. With a query, searches for matching events."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional search query (e.g. 'standup', 'Alex meeting').",
                    },
                    "days": {
                        "type": "integer",
                        "description": "How many days ahead to look (default 7).",
                    },
                },
                "required": [],
            },
            fn=check_calendar,
        ),
    ]
