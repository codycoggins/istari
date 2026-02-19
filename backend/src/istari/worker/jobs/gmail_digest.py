"""Gmail digest job — runs at 8am and 2pm daily."""

import asyncio
import logging

from istari.agents.proactive import proactive_graph
from istari.config.settings import settings
from istari.db.session import async_session_factory
from istari.tools.notification.manager import NotificationManager

logger = logging.getLogger(__name__)


async def run_gmail_digest() -> None:
    """Scan Gmail, produce actionable digest, queue as notification."""
    result = await proactive_graph.ainvoke({
        "task_type": "gmail_digest",
        "gmail_token_path": settings.gmail_token_path,
        "gmail_max_results": settings.gmail_max_results,
    })

    notifications = result.get("notifications", [])
    if not notifications:
        logger.info("Gmail digest produced no notifications")
        return

    async with async_session_factory() as session:
        mgr = NotificationManager(session)
        for notif in notifications:
            await mgr.create(type=notif["type"], content=notif["content"])
        await session.commit()
        logger.info("Gmail digest created %d notification(s)", len(notifications))


def gmail_digest_sync() -> None:
    """Sync wrapper for APScheduler (which uses a blocking scheduler)."""
    asyncio.run(run_gmail_digest())
