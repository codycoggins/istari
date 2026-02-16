"""Tests for NotificationManager — CRUD against SQLite test DB."""

from istari.tools.notification.manager import NotificationManager


class TestNotificationManagerCRUD:
    async def test_create_notification(self, db_session):
        mgr = NotificationManager(db_session)
        n = await mgr.create("digest", "Your morning digest is ready")
        assert n.id is not None
        assert n.type == "digest"
        assert n.content == "Your morning digest is ready"
        assert n.read is False
        assert n.read_at is None

    async def test_create_with_suppressed_by(self, db_session):
        mgr = NotificationManager(db_session)
        n = await mgr.create("staleness", "Stale TODO", suppressed_by="quiet_hours")
        assert n.suppressed_by == "quiet_hours"

    async def test_list_recent(self, db_session):
        mgr = NotificationManager(db_session)
        await mgr.create("digest", "First")
        await mgr.create("staleness", "Second")
        notifications = await mgr.list_recent()
        assert len(notifications) == 2

    async def test_list_recent_respects_limit(self, db_session):
        mgr = NotificationManager(db_session)
        for i in range(5):
            await mgr.create("digest", f"Notification {i}")
        notifications = await mgr.list_recent(limit=3)
        assert len(notifications) == 3

    async def test_list_recent_exclude_read(self, db_session):
        mgr = NotificationManager(db_session)
        await mgr.create("digest", "Unread one")
        n2 = await mgr.create("digest", "Will be read")
        await mgr.mark_read(n2.id)
        notifications = await mgr.list_recent(include_read=False)
        assert len(notifications) == 1
        assert notifications[0].content == "Unread one"

    async def test_get_unread_count(self, db_session):
        mgr = NotificationManager(db_session)
        await mgr.create("digest", "One")
        await mgr.create("digest", "Two")
        assert await mgr.get_unread_count() == 2

    async def test_get_unread_count_after_read(self, db_session):
        mgr = NotificationManager(db_session)
        n = await mgr.create("digest", "Will read")
        await mgr.create("digest", "Stay unread")
        await mgr.mark_read(n.id)
        assert await mgr.get_unread_count() == 1

    async def test_mark_read(self, db_session):
        mgr = NotificationManager(db_session)
        n = await mgr.create("digest", "Read me")
        result = await mgr.mark_read(n.id)
        assert result is not None
        assert result.read is True
        assert result.read_at is not None

    async def test_mark_read_nonexistent_returns_none(self, db_session):
        mgr = NotificationManager(db_session)
        assert await mgr.mark_read(9999) is None

    async def test_mark_all_read(self, db_session):
        mgr = NotificationManager(db_session)
        await mgr.create("digest", "One")
        await mgr.create("staleness", "Two")
        await mgr.create("pattern", "Three")
        count = await mgr.mark_all_read()
        assert count == 3
        assert await mgr.get_unread_count() == 0

    async def test_mark_all_read_skips_already_read(self, db_session):
        mgr = NotificationManager(db_session)
        n = await mgr.create("digest", "Already read")
        await mgr.mark_read(n.id)
        await mgr.create("digest", "Still unread")
        count = await mgr.mark_all_read()
        assert count == 1

    async def test_list_recent_returns_most_recent_first(self, db_session):
        mgr = NotificationManager(db_session)
        await mgr.create("digest", "Older")
        await mgr.create("digest", "Newer")
        notifications = await mgr.list_recent()
        assert len(notifications) == 2
        # Most recently inserted should have higher ID
        assert notifications[0].id > notifications[1].id
