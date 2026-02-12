"""User settings endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/")
async def get_settings() -> dict:
    return {"settings": {}}
