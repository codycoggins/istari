"""Tests for AppleCalendarReader — EventKit mocked so tests run on any OS."""

import datetime
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Module-level EventKit / Foundation mocks
# Must be in place before AppleCalendarReader is imported.
# ---------------------------------------------------------------------------

def _make_mock_modules() -> tuple[MagicMock, MagicMock]:
    """Build minimal EventKit and Foundation mocks."""
    mock_ek = MagicMock()
    mock_ek.EKEntityTypeEvent = 0
    mock_ek.EKAuthorizationStatusAuthorized = 3

    # authorizationStatusForEntityType_ returns 3 (authorized) by default
    mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 3

    mock_foundation = MagicMock()

    def _ns_date_factory(ts: float) -> MagicMock:
        ns = MagicMock()
        ns.timeIntervalSince1970.return_value = ts
        return ns

    mock_foundation.NSDate.dateWithTimeIntervalSince1970_.side_effect = _ns_date_factory

    return mock_ek, mock_foundation


def _make_ek_event(
    title: str,
    start_ts: float,
    end_ts: float,
    *,
    location: str = "",
    notes: str = "",
    all_day: bool = False,
    event_id: str = "abc123",
    organizer_name: str = "",
) -> MagicMock:
    """Build a mock EKEvent."""
    event = MagicMock()
    event.title.return_value = title
    event.eventIdentifier.return_value = event_id
    event.isAllDay.return_value = all_day
    event.location.return_value = location or None
    event.notes.return_value = notes or None

    start_ns = MagicMock()
    start_ns.timeIntervalSince1970.return_value = start_ts
    end_ns = MagicMock()
    end_ns.timeIntervalSince1970.return_value = end_ts
    event.startDate.return_value = start_ns
    event.endDate.return_value = end_ns

    if organizer_name:
        org = MagicMock()
        org.name.return_value = organizer_name
        event.organizer.return_value = org
    else:
        event.organizer.return_value = None

    return event


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_modules(monkeypatch: pytest.MonkeyPatch):
    mock_ek, mock_foundation = _make_mock_modules()
    monkeypatch.setitem(sys.modules, "EventKit", mock_ek)
    monkeypatch.setitem(sys.modules, "Foundation", mock_foundation)
    # Remove cached module if present
    monkeypatch.delitem(
        sys.modules,
        "istari.tools.apple_calendar.reader",
        raising=False,
    )
    return mock_ek, mock_foundation


@pytest.fixture()
def reader(mock_modules: tuple[MagicMock, MagicMock]) -> Any:
    from istari.tools.apple_calendar.reader import AppleCalendarReader
    return AppleCalendarReader()


# ---------------------------------------------------------------------------
# Import / init
# ---------------------------------------------------------------------------

class TestImport:
    def test_import_error_when_eventkit_missing(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "EventKit", None)  # type: ignore[call-overload]
        monkeypatch.delitem(
            sys.modules, "istari.tools.apple_calendar.reader", raising=False
        )
        with pytest.raises((ImportError, TypeError)):
            from istari.tools.apple_calendar.reader import AppleCalendarReader
            AppleCalendarReader()


# ---------------------------------------------------------------------------
# Access / authorization
# ---------------------------------------------------------------------------

class TestAccessControl:
    def test_no_request_when_already_authorized(
        self, reader: Any, mock_modules: tuple[MagicMock, MagicMock]
    ):
        mock_ek, _ = mock_modules
        mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 3
        # Should not raise or call request methods
        reader._ensure_access_sync()

    def test_raises_on_denied(
        self, reader: Any, mock_modules: tuple[MagicMock, MagicMock]
    ):
        mock_ek, _ = mock_modules
        mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 2
        with pytest.raises(PermissionError, match="denied"):
            reader._ensure_access_sync()

    def test_raises_on_restricted(
        self, reader: Any, mock_modules: tuple[MagicMock, MagicMock]
    ):
        mock_ek, _ = mock_modules
        mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 1
        with pytest.raises(PermissionError, match="restricted"):
            reader._ensure_access_sync()

    def test_request_full_access_on_macos14_plus(
        self, reader: Any, mock_modules: tuple[MagicMock, MagicMock]
    ):
        """Uses requestFullAccessToEventsWithCompletion_ when available."""
        mock_ek, _ = mock_modules
        mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 0

        # Simulate the async callback immediately granting access
        def grant_immediately(callback: Any) -> None:
            callback(True, None)

        reader._store.requestFullAccessToEventsWithCompletion_ = grant_immediately
        # Remove old API so hasattr check routes to new one
        del reader._store.requestAccessToEntityType_completion_

        reader._ensure_access_sync()  # should not raise

    def test_falls_back_to_old_api(
        self, reader: Any, mock_modules: tuple[MagicMock, MagicMock]
    ):
        """Falls back to requestAccessToEntityType_completion_ on older macOS."""
        mock_ek, _ = mock_modules
        mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 0

        # Remove new API from the store instance
        if hasattr(reader._store, "requestFullAccessToEventsWithCompletion_"):
            del reader._store.requestFullAccessToEventsWithCompletion_

        def grant_immediately(entity_type: Any, callback: Any) -> None:
            callback(True, None)

        reader._store.requestAccessToEntityType_completion_ = grant_immediately

        reader._ensure_access_sync()

    def test_raises_if_request_not_granted(
        self, reader: Any, mock_modules: tuple[MagicMock, MagicMock]
    ):
        mock_ek, _ = mock_modules
        mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 0

        def deny(callback: Any) -> None:
            callback(False, None)

        reader._store.requestFullAccessToEventsWithCompletion_ = deny

        with pytest.raises(PermissionError):
            reader._ensure_access_sync()


# ---------------------------------------------------------------------------
# Event parsing
# ---------------------------------------------------------------------------

class TestParseEvent:
    def test_basic_fields(self, reader: Any):
        ts_start = datetime.datetime(2026, 3, 1, 9, 0, tzinfo=datetime.UTC)
        ts_end = datetime.datetime(2026, 3, 1, 10, 0, tzinfo=datetime.UTC)
        event = _make_ek_event(
            "Team standup",
            ts_start.timestamp(),
            ts_end.timestamp(),
            location="Zoom",
            event_id="evt-001",
        )
        from istari.tools.apple_calendar.reader import AppleCalendarReader
        result = AppleCalendarReader._parse_event(event)

        assert result.summary == "Team standup"
        assert result.id == "evt-001"
        assert result.location == "Zoom"
        assert result.all_day is False
        assert result.start == ts_start
        assert result.end == ts_end

    def test_all_day_event(self, reader: Any):
        ts = datetime.datetime(2026, 3, 15, 0, 0, tzinfo=datetime.UTC)
        event = _make_ek_event("Birthday", ts.timestamp(), ts.timestamp(), all_day=True)
        from istari.tools.apple_calendar.reader import AppleCalendarReader
        result = AppleCalendarReader._parse_event(event)
        assert result.all_day is True

    def test_organizer_extracted(self, reader: Any):
        ts = datetime.datetime(2026, 3, 1, 9, 0, tzinfo=datetime.UTC)
        event = _make_ek_event(
            "1:1", ts.timestamp(), ts.timestamp(), organizer_name="Alice"
        )
        from istari.tools.apple_calendar.reader import AppleCalendarReader
        result = AppleCalendarReader._parse_event(event)
        assert result.organizer == "Alice"

    def test_no_organizer(self, reader: Any):
        ts = datetime.datetime(2026, 3, 1, 9, 0, tzinfo=datetime.UTC)
        event = _make_ek_event("Solo task", ts.timestamp(), ts.timestamp())
        from istari.tools.apple_calendar.reader import AppleCalendarReader
        result = AppleCalendarReader._parse_event(event)
        assert result.organizer == ""

    def test_empty_title(self, reader: Any):
        ts = datetime.datetime(2026, 3, 1, 9, 0, tzinfo=datetime.UTC)
        event = _make_ek_event("", ts.timestamp(), ts.timestamp())
        from istari.tools.apple_calendar.reader import AppleCalendarReader
        result = AppleCalendarReader._parse_event(event)
        assert result.summary == ""


# ---------------------------------------------------------------------------
# list_upcoming
# ---------------------------------------------------------------------------

class TestListUpcoming:
    async def test_returns_events_sorted_by_start(
        self, reader: Any, mock_modules: tuple[MagicMock, MagicMock]
    ):
        mock_ek, _ = mock_modules
        mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 3

        base = datetime.datetime(2026, 3, 1, tzinfo=datetime.UTC)
        ev1 = _make_ek_event("Later event", (base + datetime.timedelta(hours=5)).timestamp(),
                             (base + datetime.timedelta(hours=6)).timestamp(), event_id="e1")
        ev2 = _make_ek_event("Earlier event", (base + datetime.timedelta(hours=1)).timestamp(),
                             (base + datetime.timedelta(hours=2)).timestamp(), event_id="e2")

        reader._store.calendarsForEntityType_.return_value = []
        reader._store.predicateForEventsWithStartDate_endDate_calendars_.return_value = MagicMock()
        reader._store.eventsMatchingPredicate_.return_value = [ev1, ev2]

        events = await reader.list_upcoming(days=7, max_results=10)

        assert len(events) == 2
        assert events[0].id == "e2"  # earlier first
        assert events[1].id == "e1"

    async def test_max_results_limits_output(
        self, reader: Any, mock_modules: tuple[MagicMock, MagicMock]
    ):
        mock_ek, _ = mock_modules
        mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 3

        base = datetime.datetime(2026, 3, 1, tzinfo=datetime.UTC).timestamp()
        events_raw = [
            _make_ek_event(f"Event {i}", base + i * 3600, base + i * 3600 + 1800)
            for i in range(10)
        ]

        reader._store.calendarsForEntityType_.return_value = []
        reader._store.predicateForEventsWithStartDate_endDate_calendars_.return_value = MagicMock()
        reader._store.eventsMatchingPredicate_.return_value = events_raw

        events = await reader.list_upcoming(max_results=3)
        assert len(events) == 3

    async def test_returns_empty_list_when_no_events(
        self, reader: Any, mock_modules: tuple[MagicMock, MagicMock]
    ):
        mock_ek, _ = mock_modules
        mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 3

        reader._store.calendarsForEntityType_.return_value = []
        reader._store.predicateForEventsWithStartDate_endDate_calendars_.return_value = MagicMock()
        reader._store.eventsMatchingPredicate_.return_value = []

        events = await reader.list_upcoming()
        assert events == []


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

class TestSearch:
    def _setup_events(self, reader: Any) -> None:
        base = datetime.datetime(2026, 3, 1, tzinfo=datetime.UTC).timestamp()
        events = [
            _make_ek_event("Team standup", base, base + 1800, event_id="e1"),
            _make_ek_event("Dentist appointment", base + 7200, base + 9000, event_id="e2"),
            _make_ek_event("Budget review", base + 3600, base + 5400,
                           notes="Discuss Q1 budget", event_id="e3"),
        ]
        reader._store.calendarsForEntityType_.return_value = []
        reader._store.predicateForEventsWithStartDate_endDate_calendars_.return_value = MagicMock()
        reader._store.eventsMatchingPredicate_.return_value = events

    async def test_matches_title(
        self, reader: Any, mock_modules: tuple[MagicMock, MagicMock]
    ):
        mock_ek, _ = mock_modules
        mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 3
        self._setup_events(reader)

        results = await reader.search("standup")
        assert len(results) == 1
        assert results[0].id == "e1"

    async def test_matches_notes(
        self, reader: Any, mock_modules: tuple[MagicMock, MagicMock]
    ):
        mock_ek, _ = mock_modules
        mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 3
        self._setup_events(reader)

        results = await reader.search("Q1 budget")
        assert len(results) == 1
        assert results[0].id == "e3"

    async def test_case_insensitive(
        self, reader: Any, mock_modules: tuple[MagicMock, MagicMock]
    ):
        mock_ek, _ = mock_modules
        mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 3
        self._setup_events(reader)

        results = await reader.search("DENTIST")
        assert len(results) == 1
        assert results[0].id == "e2"

    async def test_no_match_returns_empty(
        self, reader: Any, mock_modules: tuple[MagicMock, MagicMock]
    ):
        mock_ek, _ = mock_modules
        mock_ek.EKEventStore.authorizationStatusForEntityType_.return_value = 3
        self._setup_events(reader)

        results = await reader.search("nonexistent xyz")
        assert results == []
