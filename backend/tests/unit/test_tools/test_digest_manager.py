"""Tests for DigestManager CRUD operations."""

import pytest

from istari.tools.digest.manager import DigestManager


@pytest.mark.asyncio
async def test_create_digest(db_session):
    mgr = DigestManager(db_session)
    digest = await mgr.create(
        source="gmail_digest",
        content_summary="3 unread emails need attention.",
    )
    assert digest.id is not None
    assert digest.source == "gmail_digest"
    assert digest.content_summary == "3 unread emails need attention."
    assert digest.reviewed is False


@pytest.mark.asyncio
async def test_list_recent(db_session):
    mgr = DigestManager(db_session)
    await mgr.create(source="gmail_digest", content_summary="Digest 1")
    await mgr.create(source="todo_staleness", content_summary="Digest 2")
    await mgr.create(source="morning_digest", content_summary="Digest 3")

    digests = await mgr.list_recent(limit=2)
    assert len(digests) == 2
    # Most recent first
    assert digests[0].content_summary == "Digest 3"


@pytest.mark.asyncio
async def test_list_recent_empty(db_session):
    mgr = DigestManager(db_session)
    digests = await mgr.list_recent()
    assert digests == []


@pytest.mark.asyncio
async def test_mark_reviewed(db_session):
    mgr = DigestManager(db_session)
    digest = await mgr.create(source="gmail_digest", content_summary="Test")

    reviewed = await mgr.mark_reviewed(digest.id)
    assert reviewed is not None
    assert reviewed.reviewed is True
    assert reviewed.reviewed_at is not None


@pytest.mark.asyncio
async def test_mark_reviewed_nonexistent(db_session):
    mgr = DigestManager(db_session)
    result = await mgr.mark_reviewed(99999)
    assert result is None
