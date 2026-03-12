"""Proactive project staleness check — surfaces stale active projects as notifications."""

import asyncio
import logging

from istari.config.settings import settings
from istari.db.session import async_session_factory
from istari.tools.notification.manager import NotificationManager
from istari.tools.project.manager import ProjectManager

logger = logging.getLogger(__name__)


async def check_stale_projects() -> None:
    """Find active projects with no recent activity and queue nudge notifications."""
    days = settings.project_staleness_days

    async with async_session_factory() as session:
        proj_mgr = ProjectManager(session)
        stale = await proj_mgr.get_stale(days=days)

        if not stale:
            logger.info("Project staleness check: no stale projects found")
            return

        notif_mgr = NotificationManager(session)
        for project in stale:
            content = (
                f"**{project.name}** is important to you but hasn't moved in "
                f"{days} days. Want to figure out the next action?"
            )
            await notif_mgr.create(type="project_staleness", content=content)

        await session.commit()
        logger.info("Project staleness check created %d notification(s)", len(stale))


def project_staleness_sync() -> None:
    """Sync wrapper for APScheduler."""
    asyncio.run(check_stale_projects())
