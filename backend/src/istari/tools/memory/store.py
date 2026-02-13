"""Memory store tool — read/write/search the memory layer (internal write, not external)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from istari.models.memory import Memory, MemoryType


class MemoryStore:
    """Explicit memory storage backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def store(self, content: str, source: str = "chat") -> Memory:
        """Store an explicit memory with confidence=1.0."""
        memory = Memory(
            type=MemoryType.EXPLICIT,
            content=content,
            confidence=1.0,
            source=source,
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
        """Search memories by content (ILIKE for Phase 1, pgvector in Phase 3)."""
        stmt = (
            select(Memory)
            .where(Memory.content.ilike(f"%{query}%"))
            .order_by(Memory.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
