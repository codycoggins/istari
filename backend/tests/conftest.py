"""Shared test fixtures: test DB, sessions, mocks."""

import pytest
from pgvector.sqlalchemy import Vector
from sqlalchemy import Text, event
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_session():
    """Async SQLite session for unit tests.

    Adapts PostgreSQL-specific column types (Vector, ARRAY, JSON) to
    SQLite-compatible equivalents so models can be tested without PostgreSQL.
    """
    from istari.models.base import Base

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    from sqlalchemy import event as sa_event

    @sa_event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    async with engine.begin() as conn:

        def _create_tables(sync_conn):  # type: ignore[no-untyped-def]
            for table in Base.metadata.tables.values():
                for column in table.columns:
                    if isinstance(column.type, (Vector, ARRAY, JSON)):
                        column.type = Text()
            Base.metadata.create_all(sync_conn)

        await conn.run_sync(_create_tables)

    async with engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)

        @event.listens_for(session.sync_session, "after_transaction_end")
        def restart_savepoint(session_sync, transaction):  # type: ignore[no-untyped-def]
            if transaction.nested and not transaction._parent.nested:
                session_sync.begin_nested()

        await conn.begin_nested()

        yield session

        await session.close()
        await conn.rollback()

    await engine.dispose()
