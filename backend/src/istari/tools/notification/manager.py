"""Notification manager — CRUD for notification queue."""

import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from istari.models.notification import Notification


class NotificationManager:
    """CRUD operations for notifications backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        type: str,
        content: str,
        suppressed_by: str | None = None,
    ) -> Notification:
        notification = Notification(
            type=type,
            content=content,
            suppressed_by=suppressed_by,
        )
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def list_recent(
        self,
        limit: int = 20,
        include_read: bool = True,
        exclude_completed_before: datetime.datetime | None = None,
    ) -> list[Notification]:
        stmt = (
            select(Notification)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
        )
        if not include_read:
            stmt = stmt.where(Notification.read.is_(False))
        if exclude_completed_before is not None:
            stmt = stmt.where(
                (Notification.completed.is_(False))
                | (Notification.completed_at >= exclude_completed_before)
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_unread_count(self) -> int:
        stmt = select(func.count(Notification.id)).where(Notification.read.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def mark_read(self, notification_id: int) -> Notification | None:
        notification = await self.session.get(Notification, notification_id)
        if notification is None:
            return None
        notification.read = True
        notification.read_at = datetime.datetime.now(datetime.UTC)
        await self.session.flush()
        return notification

    async def mark_completed(self, notification_id: int) -> Notification | None:
        notification = await self.session.get(Notification, notification_id)
        if notification is None:
            return None
        notification.completed = True
        notification.completed_at = datetime.datetime.now(datetime.UTC)
        await self.session.flush()
        return notification

    async def mark_all_read(self) -> int:
        now = datetime.datetime.now(datetime.UTC)
        stmt = (
            update(Notification)
            .where(Notification.read.is_(False))
            .values(read=True, read_at=now)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount  # type: ignore[attr-defined, no-any-return]
