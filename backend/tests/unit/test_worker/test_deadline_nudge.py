"""Tests for the deadline nudge worker job."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_check_deadline_todos_creates_notifications():
    """Todos due soon generate nudge notifications."""
    now = datetime.datetime.now(datetime.UTC)
    mock_todo = MagicMock()
    mock_todo.title = "Pay taxes"
    mock_todo.due_date = now + datetime.timedelta(days=2)

    mock_session = AsyncMock()
    mock_session_factory = AsyncMock()
    mock_session_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "istari.worker.jobs.deadline_nudge.async_session_factory",
            return_value=mock_session_factory,
        ),
        patch("istari.worker.jobs.deadline_nudge.TodoManager") as mock_todo_cls,
        patch(
            "istari.worker.jobs.deadline_nudge.NotificationManager"
        ) as mock_notif_cls,
        patch("istari.worker.jobs.deadline_nudge.settings") as mock_settings,
    ):
        mock_settings.deadline_nudge_days = 3

        mock_todo_mgr = MagicMock()
        mock_todo_mgr.get_due_soon = AsyncMock(return_value=[mock_todo])
        mock_todo_cls.return_value = mock_todo_mgr

        mock_notif_mgr = MagicMock()
        mock_notif_mgr.create = AsyncMock()
        mock_notif_cls.return_value = mock_notif_mgr

        from istari.worker.jobs.deadline_nudge import check_deadline_todos

        await check_deadline_todos()

        mock_todo_mgr.get_due_soon.assert_called_once_with(days=3)
        mock_notif_mgr.create.assert_called_once()
        call_kwargs = mock_notif_mgr.create.call_args
        assert call_kwargs.kwargs["type"] == "deadline_nudge"
        assert "Pay taxes" in call_kwargs.kwargs["content"]
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_check_deadline_todos_no_due():
    """No todos due → no notifications, no DB writes."""
    mock_session = AsyncMock()
    mock_session_factory = AsyncMock()
    mock_session_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "istari.worker.jobs.deadline_nudge.async_session_factory",
            return_value=mock_session_factory,
        ),
        patch("istari.worker.jobs.deadline_nudge.TodoManager") as mock_todo_cls,
        patch(
            "istari.worker.jobs.deadline_nudge.NotificationManager"
        ) as mock_notif_cls,
        patch("istari.worker.jobs.deadline_nudge.settings") as mock_settings,
    ):
        mock_settings.deadline_nudge_days = 3

        mock_todo_mgr = MagicMock()
        mock_todo_mgr.get_due_soon = AsyncMock(return_value=[])
        mock_todo_cls.return_value = mock_todo_mgr

        mock_notif_mgr = MagicMock()
        mock_notif_cls.return_value = mock_notif_mgr

        from istari.worker.jobs.deadline_nudge import check_deadline_todos

        await check_deadline_todos()

        mock_notif_mgr.create.assert_not_called()
        mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_check_deadline_todos_overdue_message():
    """Overdue todos include 'overdue' wording in notification."""
    now = datetime.datetime.now(datetime.UTC)
    mock_todo = MagicMock()
    mock_todo.title = "Overdue task"
    mock_todo.due_date = now - datetime.timedelta(days=2)

    mock_session = AsyncMock()
    mock_session_factory = AsyncMock()
    mock_session_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "istari.worker.jobs.deadline_nudge.async_session_factory",
            return_value=mock_session_factory,
        ),
        patch("istari.worker.jobs.deadline_nudge.TodoManager") as mock_todo_cls,
        patch(
            "istari.worker.jobs.deadline_nudge.NotificationManager"
        ) as mock_notif_cls,
        patch("istari.worker.jobs.deadline_nudge.settings") as mock_settings,
    ):
        mock_settings.deadline_nudge_days = 3

        mock_todo_mgr = MagicMock()
        mock_todo_mgr.get_due_soon = AsyncMock(return_value=[mock_todo])
        mock_todo_cls.return_value = mock_todo_mgr

        mock_notif_mgr = MagicMock()
        mock_notif_mgr.create = AsyncMock()
        mock_notif_cls.return_value = mock_notif_mgr

        from istari.worker.jobs.deadline_nudge import check_deadline_todos

        await check_deadline_todos()

        call_kwargs = mock_notif_mgr.create.call_args
        assert "overdue" in call_kwargs.kwargs["content"].lower()


@pytest.mark.asyncio
async def test_check_deadline_todos_multiple():
    """Multiple due-soon todos each get a notification."""
    now = datetime.datetime.now(datetime.UTC)
    todos = []
    for i, name in enumerate(["Task A", "Task B", "Task C"]):
        m = MagicMock()
        m.title = name
        m.due_date = now + datetime.timedelta(days=i + 1)
        todos.append(m)

    mock_session = AsyncMock()
    mock_session_factory = AsyncMock()
    mock_session_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "istari.worker.jobs.deadline_nudge.async_session_factory",
            return_value=mock_session_factory,
        ),
        patch("istari.worker.jobs.deadline_nudge.TodoManager") as mock_todo_cls,
        patch(
            "istari.worker.jobs.deadline_nudge.NotificationManager"
        ) as mock_notif_cls,
        patch("istari.worker.jobs.deadline_nudge.settings") as mock_settings,
    ):
        mock_settings.deadline_nudge_days = 3

        mock_todo_mgr = MagicMock()
        mock_todo_mgr.get_due_soon = AsyncMock(return_value=todos)
        mock_todo_cls.return_value = mock_todo_mgr

        mock_notif_mgr = MagicMock()
        mock_notif_mgr.create = AsyncMock()
        mock_notif_cls.return_value = mock_notif_mgr

        from istari.worker.jobs.deadline_nudge import check_deadline_todos

        await check_deadline_todos()

        assert mock_notif_mgr.create.call_count == 3
        mock_session.commit.assert_called_once()
