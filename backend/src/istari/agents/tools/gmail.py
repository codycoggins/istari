"""Gmail agent tools — read and search email."""

import logging

from .base import AgentTool

logger = logging.getLogger(__name__)


def make_gmail_tools() -> list[AgentTool]:
    """Return Gmail tools. No session needed — uses OAuth token from settings."""

    async def check_email(query: str = "") -> str:
        from istari.config.settings import settings
        from istari.tools.gmail.reader import GmailReader

        try:
            reader = GmailReader(settings.gmail_token_path)
            if query:
                emails = await reader.search(query, max_results=settings.gmail_max_results)
            else:
                emails = await reader.list_unread(max_results=settings.gmail_max_results)
        except FileNotFoundError:
            return (
                "Gmail isn't connected yet. Run `python scripts/setup_gmail.py` "
                "to link your Gmail account."
            )
        except Exception:
            logger.exception("Gmail tool error")
            return "Couldn't reach Gmail. Try again in a moment."

        if not emails:
            return "No unread emails found." if not query else f'No emails matching "{query}".'

        lines = [f"- {e.subject} (from {e.sender}): {e.snippet}" for e in emails]
        return f"Found {len(emails)} email(s):\n" + "\n".join(lines)

    return [
        AgentTool(
            name="check_email",
            description=(
                "Check the user's Gmail. With no query, returns unread emails. "
                "With a query, searches all mail for matching emails."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional search query. Leave empty for unread emails.",
                    }
                },
                "required": [],
            },
            fn=check_email,
        ),
    ]
