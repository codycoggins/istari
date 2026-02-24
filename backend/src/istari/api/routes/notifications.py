"""Notification endpoints — read notifications queued by the worker."""

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from istari.api.deps import get_db
from istari.api.schemas import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from istari.tools.notification.manager import NotificationManager

router = APIRouter(prefix="/notifications", tags=["notifications"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    db: DB, limit: int = 20, unread_only: bool = False
) -> NotificationListResponse:
    mgr = NotificationManager(db)
    now = datetime.datetime.now(datetime.UTC)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    notifications = await mgr.list_recent(
        limit=limit,
        include_read=not unread_only,
        exclude_completed_before=start_of_today,
    )
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
    )


@router.get("/unread/count", response_model=UnreadCountResponse)
async def get_unread_count(db: DB) -> UnreadCountResponse:
    mgr = NotificationManager(db)
    count = await mgr.get_unread_count()
    return UnreadCountResponse(count=count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(notification_id: int, db: DB) -> NotificationResponse:
    mgr = NotificationManager(db)
    notification = await mgr.mark_read(notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.commit()
    await db.refresh(notification)
    return NotificationResponse.model_validate(notification)


@router.post("/{notification_id}/complete", response_model=NotificationResponse)
async def complete_notification(notification_id: int, db: DB) -> NotificationResponse:
    mgr = NotificationManager(db)
    notification = await mgr.mark_completed(notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.commit()
    await db.refresh(notification)
    return NotificationResponse.model_validate(notification)


@router.post("/read-all", response_model=UnreadCountResponse)
async def mark_all_read(db: DB) -> UnreadCountResponse:
    mgr = NotificationManager(db)
    count = await mgr.mark_all_read()
    await db.commit()
    return UnreadCountResponse(count=count)
