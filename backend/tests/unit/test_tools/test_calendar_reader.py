"""Tests for CalendarReader — all Google API calls are mocked."""

import datetime
from unittest.mock import MagicMock, patch

import pytest

from istari.tools.calendar.reader import CalendarEvent, CalendarReader


@pytest.fixture()
def mock_service():
    """Return a mock Calendar API service."""
    return MagicMock()


@pytest.fixture()
def reader(tmp_path, mock_service):
    """Create a CalendarReader with a fake token file and mocked service."""
    token_file = tmp_path / "calendar_token.json"
    token_file.write_text(
        '{"token": "fake", "refresh_token": "fake",'
        ' "client_id": "x", "client_secret": "y",'
        ' "scopes": ["https://www.googleapis.com/auth/calendar.readonly"]}'
    )
    creds_path = "istari.tools.calendar.reader.Credentials.from_authorized_user_file"
    with (
        patch(creds_path) as mock_creds_cls,
        patch("istari.tools.calendar.reader.build", return_value=mock_service),
    ):
        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds_cls.return_value = mock_creds
        r = CalendarReader(str(token_file))
    return r


def _make_event(
    event_id: str,
    summary: str,
    start_dt: str,
    end_dt: str,
    location: str = "",
    organizer: str = "me@test.com",
) -> dict:
    return {
        "id": event_id,
        "summary": summary,
        "start": {"dateTime": start_dt},
        "end": {"dateTime": end_dt},
        "location": location,
        "description": "",
        "htmlLink": f"https://calendar.google.com/event?eid={event_id}",
        "organizer": {"email": organizer},
    }


def _make_all_day_event(event_id: str, summary: str, date: str) -> dict:
    return {
        "id": event_id,
        "summary": summary,
        "start": {"date": date},
        "end": {"date": date},
        "location": "",
        "description": "",
        "htmlLink": f"https://calendar.google.com/event?eid={event_id}",
        "organizer": {"email": "me@test.com"},
    }


@pytest.mark.asyncio
async def test_list_upcoming(reader, mock_service):
    mock_service.events().list().execute.return_value = {
        "items": [
            _make_event("e1", "Team standup", "2026-02-20T09:00:00Z", "2026-02-20T09:30:00Z"),
            _make_event("e2", "1:1 with manager", "2026-02-20T14:00:00Z", "2026-02-20T15:00:00Z"),
        ]
    }

    results = await reader.list_upcoming(days=7, max_results=10)

    assert len(results) == 2
    assert isinstance(results[0], CalendarEvent)
    assert results[0].id == "e1"
    assert results[0].summary == "Team standup"
    assert results[0].all_day is False
    assert results[1].id == "e2"


@pytest.mark.asyncio
async def test_list_upcoming_empty(reader, mock_service):
    mock_service.events().list().execute.return_value = {"items": []}

    results = await reader.list_upcoming()
    assert results == []


@pytest.mark.asyncio
async def test_search(reader, mock_service):
    mock_service.events().list().execute.return_value = {
        "items": [
            _make_event("e3", "Sprint planning", "2026-02-21T10:00:00Z", "2026-02-21T12:00:00Z"),
        ]
    }

    results = await reader.search("sprint", max_results=10)

    assert len(results) == 1
    assert results[0].summary == "Sprint planning"


@pytest.mark.asyncio
async def test_search_empty(reader, mock_service):
    mock_service.events().list().execute.return_value = {"items": []}

    results = await reader.search("nonexistent query")
    assert results == []


@pytest.mark.asyncio
async def test_get_event(reader, mock_service):
    mock_service.events().get().execute.return_value = _make_event(
        "e4",
        "Product review",
        "2026-02-22T15:00:00Z",
        "2026-02-22T16:00:00Z",
        location="Conference Room B",
    )

    result = await reader.get_event("e4")

    assert isinstance(result, CalendarEvent)
    assert result.id == "e4"
    assert result.summary == "Product review"
    assert result.location == "Conference Room B"


@pytest.mark.asyncio
async def test_all_day_event(reader, mock_service):
    mock_service.events().list().execute.return_value = {
        "items": [_make_all_day_event("e5", "Company holiday", "2026-02-20")]
    }

    results = await reader.list_upcoming()

    assert len(results) == 1
    assert results[0].all_day is True
    assert isinstance(results[0].start, datetime.date)


def test_token_not_found():
    with pytest.raises(FileNotFoundError, match="Calendar token not found"):
        CalendarReader("/nonexistent/calendar_token.json")


def test_parse_dt_datetime():
    result = CalendarReader._parse_dt({"dateTime": "2026-02-20T09:00:00+00:00"})
    assert isinstance(result, datetime.datetime)
    assert result.year == 2026
    assert result.month == 2


def test_parse_dt_date():
    result = CalendarReader._parse_dt({"date": "2026-02-20"})
    assert isinstance(result, datetime.date)
    assert result.year == 2026


def test_parse_dt_empty():
    assert CalendarReader._parse_dt({}) is None


def test_parse_dt_invalid():
    assert CalendarReader._parse_dt({"dateTime": "not-a-date"}) is None


def test_parse_event_no_summary():
    event = {
        "id": "e6",
        "start": {"dateTime": "2026-02-20T09:00:00Z"},
        "end": {"dateTime": "2026-02-20T10:00:00Z"},
    }
    result = CalendarReader._parse_event(event)
    assert result.summary == "(no title)"
    assert result.location == ""
    assert result.organizer == ""
