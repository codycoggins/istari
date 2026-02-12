"""Chat/conversation endpoints (WebSocket + REST)."""

from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/")
async def get_conversations() -> dict:
    return {"conversations": []}
