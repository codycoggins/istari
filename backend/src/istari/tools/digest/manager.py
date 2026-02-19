"""Digest manager — CRUD for processed digests."""

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from istari.models.digest import Digest


class DigestManager:
    """CRUD operations for digests backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        source: str,
        content_summary: str,
        items_json: dict | None = None,
    ) -> Digest:
        digest = Digest(
            source=source,
            content_summary=content_summary,
            items_json=items_json,
        )
        self.session.add(digest)
        await self.session.flush()
        return digest

    async def list_recent(self, limit: int = 10) -> list[Digest]:
        stmt = (
            select(Digest)
            .order_by(Digest.created_at.desc(), Digest.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_reviewed(self, digest_id: int) -> Digest | None:
        digest = await self.session.get(Digest, digest_id)
        if digest is None:
            return None
        digest.reviewed = True
        digest.reviewed_at = datetime.datetime.now(datetime.UTC)
        await self.session.flush()
        return digest
