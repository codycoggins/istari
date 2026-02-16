"""Notification endpoints — read notifications queued by the worker."""

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
async def list_notifications(db: DB, limit: int = 20, unread_only: bool = False):
    mgr = NotificationManager(db)
    notifications = await mgr.list_recent(limit=limit, include_read=not unread_only)
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
    )


@router.get("/unread/count", response_model=UnreadCountResponse)
async def get_unread_count(db: DB):
    mgr = NotificationManager(db)
    count = await mgr.get_unread_count()
    return UnreadCountResponse(count=count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(notification_id: int, db: DB):
    mgr = NotificationManager(db)
    notification = await mgr.mark_read(notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.commit()
    return NotificationResponse.model_validate(notification)


@router.post("/read-all", response_model=UnreadCountResponse)
async def mark_all_read(db: DB):
    mgr = NotificationManager(db)
    count = await mgr.mark_all_read()
    await db.commit()
    return UnreadCountResponse(count=count)
