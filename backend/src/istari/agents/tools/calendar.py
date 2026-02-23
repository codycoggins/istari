"""Calendar agent tools — read and search calendar events.

Routes to AppleCalendarReader or CalendarReader (Google) based on
the CALENDAR_BACKEND setting ("apple" or "google").
"""

import logging

from .base import AgentTool

logger = logging.getLogger(__name__)


def make_calendar_tools() -> list[AgentTool]:
    """Return Calendar tools. No session needed."""

    async def check_calendar(query: str = "", days: int = 7) -> str:
        from istari.config.settings import settings

        max_r = settings.calendar_max_results

        try:
            if settings.calendar_backend == "apple":
                from istari.tools.apple_calendar.reader import AppleCalendarReader
                reader = AppleCalendarReader()
            else:
                from istari.tools.calendar.reader import CalendarReader
                reader = CalendarReader(settings.calendar_token_path)

            if query:
                events = await reader.search(query, max_results=max_r)
            else:
                events = await reader.list_upcoming(days=days, max_results=max_r)

        except ImportError as exc:
            return f"Calendar backend unavailable: {exc}"
        except FileNotFoundError:
            return (
                "Google Calendar isn't connected yet. "
                "Run `python scripts/setup_calendar.py` to link your calendar."
            )
        except PermissionError as exc:
            return str(exc)
        except Exception:
            logger.exception("Calendar tool error")
            return "Couldn't reach your calendar. Try again in a moment."

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

    backend_label = "calendar (Apple or Google depending on CALENDAR_BACKEND setting)"
    return [
        AgentTool(
            name="check_calendar",
            description=(
                f"Check the user's {backend_label}. With no query, returns upcoming "
                "events for the next `days` days. With a query, searches for matching events."
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
