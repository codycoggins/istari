"""Notification endpoints — read notifications queued by the worker."""

from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
async def list_notifications() -> dict:
    return {"notifications": []}
