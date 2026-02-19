"""Tests for worker jobs — gmail digest and staleness check."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_run_gmail_digest_creates_notifications():
    mock_result = {
        "notifications": [{"type": "gmail_digest", "content": "3 unread emails."}],
    }

    mock_session = AsyncMock()
    mock_session_factory = AsyncMock()
    mock_session_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("istari.worker.jobs.gmail_digest.proactive_graph") as mock_graph,
        patch("istari.worker.jobs.gmail_digest.async_session_factory",
              return_value=mock_session_factory),
        patch("istari.worker.jobs.gmail_digest.NotificationManager") as mock_mgr_cls,
    ):
        mock_graph.ainvoke = AsyncMock(return_value=mock_result)
        mock_mgr = MagicMock()
        mock_mgr.create = AsyncMock()
        mock_mgr_cls.return_value = mock_mgr

        from istari.worker.jobs.gmail_digest import run_gmail_digest

        await run_gmail_digest()

        mock_mgr.create.assert_called_once_with(type="gmail_digest", content="3 unread emails.")
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_run_gmail_digest_no_notifications():
    mock_result = {"notifications": []}

    with patch("istari.worker.jobs.gmail_digest.proactive_graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value=mock_result)

        from istari.worker.jobs.gmail_digest import run_gmail_digest

        await run_gmail_digest()
        # Should not attempt DB writes


@pytest.mark.asyncio
async def test_check_stale_todos_creates_notifications():
    mock_result = {
        "notifications": [{"type": "todo_staleness", "content": "2 stale TODOs."}],
    }

    mock_session = AsyncMock()
    mock_session_factory = AsyncMock()
    mock_session_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("istari.worker.jobs.staleness.proactive_graph") as mock_graph,
        patch("istari.worker.jobs.staleness.async_session_factory",
              return_value=mock_session_factory),
        patch("istari.worker.jobs.staleness.NotificationManager") as mock_mgr_cls,
    ):
        mock_graph.ainvoke = AsyncMock(return_value=mock_result)
        mock_mgr = MagicMock()
        mock_mgr.create = AsyncMock()
        mock_mgr_cls.return_value = mock_mgr

        from istari.worker.jobs.staleness import check_stale_todos

        await check_stale_todos()

        mock_mgr.create.assert_called_once_with(type="todo_staleness", content="2 stale TODOs.")
        mock_session.commit.assert_called_once()


def test_quiet_hours_skip():
    """Test that the quiet hours wrapper skips job execution."""
    import datetime

    from istari.worker.main import respect_quiet_hours

    fn = MagicMock(__name__="test_fn")
    wrapped = respect_quiet_hours(fn)

    # Simulate quiet hours (e.g. 22:00 with quiet 21-7)
    with patch("istari.worker.main.datetime") as mock_dt:
        mock_dt.datetime.now.return_value = datetime.datetime(
            2025, 2, 10, 22, 0, tzinfo=datetime.UTC,
        )
        mock_dt.UTC = datetime.UTC
        with patch("istari.worker.main.settings") as mock_settings:
            mock_settings.quiet_hours_start = 21
            mock_settings.quiet_hours_end = 7
            wrapped()

    fn.assert_not_called()


def test_outside_quiet_hours_runs():
    """Test that the wrapper runs the job outside quiet hours."""
    import datetime

    from istari.worker.main import respect_quiet_hours

    fn = MagicMock(__name__="test_fn")
    wrapped = respect_quiet_hours(fn)

    with patch("istari.worker.main.datetime") as mock_dt:
        mock_dt.datetime.now.return_value = datetime.datetime(
            2025, 2, 10, 10, 0, tzinfo=datetime.UTC,
        )
        mock_dt.UTC = datetime.UTC
        with patch("istari.worker.main.settings") as mock_settings:
            mock_settings.quiet_hours_start = 21
            mock_settings.quiet_hours_end = 7
            wrapped()

    fn.assert_called_once()
