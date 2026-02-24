"""User settings endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from istari.api.deps import get_db
from istari.api.schemas import SettingResponse, SettingsResponse, SettingUpdate
from istari.models.user import UserSetting

router = APIRouter(prefix="/settings", tags=["settings"])

DB = Annotated[AsyncSession, Depends(get_db)]

_DEFAULTS: dict[str, str] = {
    "quiet_hours_start": "21",
    "quiet_hours_end": "7",
    "focus_mode": "false",
}


@router.get("/", response_model=SettingsResponse)
async def get_settings(db: DB) -> SettingsResponse:
    result = await db.execute(select(UserSetting))
    rows = result.scalars().all()
    merged = dict(_DEFAULTS)
    for row in rows:
        merged[row.key] = row.value
    return SettingsResponse(settings=merged)


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(key: str, body: SettingUpdate, db: DB) -> SettingResponse:
    existing = await db.get(UserSetting, key)
    if existing:
        existing.value = body.value
    else:
        db.add(UserSetting(key=key, value=body.value))
    await db.commit()
    return SettingResponse(key=key, value=body.value)
