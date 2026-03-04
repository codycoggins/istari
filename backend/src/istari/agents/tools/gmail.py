"""Gmail agent tools — read and search email."""

import logging

from istari.config.settings import settings
from istari.tools.gmail.reader import GmailReader

from .base import AgentTool

logger = logging.getLogger(__name__)


def make_gmail_tools() -> list[AgentTool]:
    """Return Gmail tools. No session needed — uses OAuth token from settings."""

    async def check_email(query: str = "", max_results: int = 0) -> str:
        limit = max_results or settings.gmail_max_results
        logger.info(
            "check_email | token=%s query=%r max_results=%d",
            settings.gmail_token_path, query or "<unread>", limit,
        )
        try:
            reader = GmailReader(settings.gmail_token_path)
            if query:
                emails = await reader.search(query, max_results=limit)
            else:
                emails = await reader.list_unread(max_results=limit)
        except FileNotFoundError:
            logger.error("check_email | token file not found: %s", settings.gmail_token_path)
            return (
                "Gmail isn't connected yet. Run `python scripts/setup_gmail.py` "
                "to link your Gmail account."
            )
        except Exception:
            logger.exception("check_email | unexpected error")
            return "Couldn't reach Gmail. Try again in a moment."

        if not emails:
            return "No unread emails found." if not query else f'No emails matching "{query}".'

        lines = [
            f"- [{e.subject}](https://mail.google.com/mail/u/0/#all/{e.thread_id})"
            f" (from {e.sender}): {e.snippet}"
            for e in emails
        ]
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
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max emails to return (default uses account setting).",
                    },
                },
                "required": [],
            },
            fn=check_email,
        ),
    ]
