"""TODO staleness check — batched into morning digest."""

import asyncio
import logging

from istari.agents.proactive import proactive_graph
from istari.config.settings import settings
from istari.db.session import async_session_factory
from istari.tools.notification.manager import NotificationManager

logger = logging.getLogger(__name__)


async def check_stale_todos() -> None:
    """Identify stale TODOs and surface them as a notification."""
    async with async_session_factory() as session:
        result = await proactive_graph.ainvoke({
            "task_type": "staleness_only",
            "stale_todo_days": settings.stale_todo_days,
            "db_session": session,
        })

        notifications = result.get("notifications", [])
        if not notifications:
            logger.info("Staleness check produced no notifications")
            return

        mgr = NotificationManager(session)
        for notif in notifications:
            await mgr.create(type=notif["type"], content=notif["content"])
        await session.commit()
        logger.info("Staleness check created %d notification(s)", len(notifications))


def staleness_sync() -> None:
    """Sync wrapper for APScheduler."""
    asyncio.run(check_stale_todos())
