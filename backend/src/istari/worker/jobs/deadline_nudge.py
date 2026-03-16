"""Proactive deadline nudge — surfaces todos due soon as notifications."""

import asyncio
import datetime
import logging

from istari.config.settings import settings
from istari.db.session import async_session_factory
from istari.tools.notification.manager import NotificationManager
from istari.tools.todo.manager import TodoManager

logger = logging.getLogger(__name__)


async def check_deadline_todos() -> None:
    """Find todos due within deadline_nudge_days and queue nudge notifications."""
    days = settings.deadline_nudge_days
    now = datetime.datetime.now(datetime.UTC)

    async with async_session_factory() as session:
        todo_mgr = TodoManager(session)
        due_soon = await todo_mgr.get_due_soon(days=days)

        if not due_soon:
            logger.info("Deadline nudge: no todos due within %d days", days)
            return

        notif_mgr = NotificationManager(session)
        created = 0
        for todo in due_soon:
            due = todo.due_date
            if due is None:
                continue
            if due.tzinfo is None:
                due = due.replace(tzinfo=datetime.UTC)
            diff_days = (due - now).days
            if diff_days < 0:
                time_str = f"overdue by {abs(diff_days)} day(s)"
            elif diff_days == 0:
                time_str = "due today"
            else:
                time_str = f"due in {diff_days} day(s)"
            content = (
                f"**{todo.title}** is {time_str}. "
                "Is this still on track?"
            )
            await notif_mgr.create(type="deadline_nudge", content=content)
            created += 1

        await session.commit()
        logger.info("Deadline nudge created %d notification(s)", created)


def deadline_nudge_sync() -> None:
    """Sync wrapper for APScheduler."""
    asyncio.run(check_deadline_todos())
