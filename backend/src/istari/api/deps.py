"""FastAPI dependency injection — database sessions and shared resources."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from istari.db.session import get_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session
