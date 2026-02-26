"""Memory store tool — read/write/search the memory layer (internal write, not external)."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from istari.llm.router import embedding as generate_embedding
from istari.models.memory import Memory, MemoryType

logger = logging.getLogger(__name__)


class MemoryStore:
    """Explicit memory storage backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def store(self, content: str, source: str = "chat") -> Memory:
        """Store an explicit memory with confidence=1.0."""
        vec: list[float] | None = None
        try:
            vec = await generate_embedding(content)
        except Exception:
            logger.warning("Embedding generation failed; storing without vector", exc_info=True)

        memory = Memory(
            type=MemoryType.EXPLICIT,
            content=content,
            confidence=1.0,
            source=source,
            embedding=vec,
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def list_explicit(self) -> list[Memory]:
        stmt = (
            select(Memory)
            .where(Memory.type == MemoryType.EXPLICIT)
            .order_by(Memory.created_at.desc(), Memory.id.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search(self, query: str) -> list[Memory]:
        """Search memories by content. Uses cosine similarity when embeddings available, else ILIKE.
        """
        try:
            vec = await generate_embedding(query)
            results = await self._search_semantic(vec)
            if results:
                return results
        except Exception:
            logger.debug("Semantic search unavailable, using ILIKE fallback", exc_info=True)
        return await self._search_ilike(query)

    async def _search_semantic(self, vec: list[float], top_k: int = 10) -> list[Memory]:
        stmt = (
            select(Memory)
            .where(Memory.type == MemoryType.EXPLICIT, Memory.embedding.isnot(None))
            .order_by(Memory.embedding.cosine_distance(vec))
            .limit(top_k)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _search_ilike(self, query: str, top_k: int = 10) -> list[Memory]:
        stmt = (
            select(Memory)
            .where(Memory.content.ilike(f"%{query}%"))
            .order_by(Memory.created_at.desc())
            .limit(top_k)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
