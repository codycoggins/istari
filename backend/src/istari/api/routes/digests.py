"""Digest endpoints — view and manage processed digests."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from istari.api.deps import get_db
from istari.api.schemas import DigestListResponse, DigestResponse
from istari.tools.digest.manager import DigestManager

router = APIRouter(prefix="/digests", tags=["digests"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=DigestListResponse)
async def list_digests(db: DB, limit: int = 10) -> DigestListResponse:
    mgr = DigestManager(db)
    digests = await mgr.list_recent(limit=limit)
    return DigestListResponse(
        digests=[DigestResponse.model_validate(d) for d in digests],
    )


@router.post("/{digest_id}/review", response_model=DigestResponse)
async def review_digest(digest_id: int, db: DB) -> DigestResponse:
    mgr = DigestManager(db)
    digest = await mgr.mark_reviewed(digest_id)
    if digest is None:
        raise HTTPException(status_code=404, detail="Digest not found")
    await db.commit()
    await db.refresh(digest)
    return DigestResponse.model_validate(digest)
