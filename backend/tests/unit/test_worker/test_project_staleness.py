"""Tests for the project staleness worker job."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_check_stale_projects_creates_notifications():
    """Stale projects generate one notification each."""
    mock_project = MagicMock()
    mock_project.name = "Home Renovation"

    mock_session = AsyncMock()
    mock_session_factory = AsyncMock()
    mock_session_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "istari.worker.jobs.project_staleness.async_session_factory",
            return_value=mock_session_factory,
        ),
        patch(
            "istari.worker.jobs.project_staleness.ProjectManager"
        ) as mock_proj_cls,
        patch(
            "istari.worker.jobs.project_staleness.NotificationManager"
        ) as mock_notif_cls,
        patch(
            "istari.worker.jobs.project_staleness.settings"
        ) as mock_settings,
    ):
        mock_settings.project_staleness_days = 7

        mock_proj_mgr = MagicMock()
        mock_proj_mgr.get_stale = AsyncMock(return_value=[mock_project])
        mock_proj_cls.return_value = mock_proj_mgr

        mock_notif_mgr = MagicMock()
        mock_notif_mgr.create = AsyncMock()
        mock_notif_cls.return_value = mock_notif_mgr

        from istari.worker.jobs.project_staleness import check_stale_projects

        await check_stale_projects()

        mock_proj_mgr.get_stale.assert_called_once_with(days=7)
        mock_notif_mgr.create.assert_called_once()
        call_kwargs = mock_notif_mgr.create.call_args
        assert call_kwargs.kwargs["type"] == "project_staleness"
        assert "Home Renovation" in call_kwargs.kwargs["content"]
        assert "7 days" in call_kwargs.kwargs["content"]
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_check_stale_projects_no_stale():
    """No stale projects → no notifications, no DB writes."""
    mock_session = AsyncMock()
    mock_session_factory = AsyncMock()
    mock_session_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "istari.worker.jobs.project_staleness.async_session_factory",
            return_value=mock_session_factory,
        ),
        patch(
            "istari.worker.jobs.project_staleness.ProjectManager"
        ) as mock_proj_cls,
        patch(
            "istari.worker.jobs.project_staleness.NotificationManager"
        ) as mock_notif_cls,
        patch(
            "istari.worker.jobs.project_staleness.settings"
        ) as mock_settings,
    ):
        mock_settings.project_staleness_days = 7

        mock_proj_mgr = MagicMock()
        mock_proj_mgr.get_stale = AsyncMock(return_value=[])
        mock_proj_cls.return_value = mock_proj_mgr

        mock_notif_mgr = MagicMock()
        mock_notif_cls.return_value = mock_notif_mgr

        from istari.worker.jobs.project_staleness import check_stale_projects

        await check_stale_projects()

        mock_notif_mgr.create.assert_not_called()
        mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_check_stale_projects_multiple():
    """Multiple stale projects create one notification each."""
    projects = [MagicMock(name=n) for n in ["Alpha", "Beta", "Gamma"]]
    for p, n in zip(projects, ["Alpha", "Beta", "Gamma"], strict=True):
        p.name = n

    mock_session = AsyncMock()
    mock_session_factory = AsyncMock()
    mock_session_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "istari.worker.jobs.project_staleness.async_session_factory",
            return_value=mock_session_factory,
        ),
        patch(
            "istari.worker.jobs.project_staleness.ProjectManager"
        ) as mock_proj_cls,
        patch(
            "istari.worker.jobs.project_staleness.NotificationManager"
        ) as mock_notif_cls,
        patch(
            "istari.worker.jobs.project_staleness.settings"
        ) as mock_settings,
    ):
        mock_settings.project_staleness_days = 14

        mock_proj_mgr = MagicMock()
        mock_proj_mgr.get_stale = AsyncMock(return_value=projects)
        mock_proj_cls.return_value = mock_proj_mgr

        mock_notif_mgr = MagicMock()
        mock_notif_mgr.create = AsyncMock()
        mock_notif_cls.return_value = mock_notif_mgr

        from istari.worker.jobs.project_staleness import check_stale_projects

        await check_stale_projects()

        assert mock_notif_mgr.create.call_count == 3
        mock_session.commit.assert_called_once()
