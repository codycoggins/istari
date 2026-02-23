"""Apple Calendar reader — reads events via EventKit (macOS native).

Requires: pip install pyobjc-framework-EventKit  (macOS only)

Unlike the Google Calendar integration, no OAuth flow is needed. EventKit
reads directly from Calendar.app's local database, which includes all
synced sources (iCloud, Google Calendar, Exchange, etc.) simultaneously.

First run: macOS will show a system permission dialog. If the process
cannot display the dialog (e.g. a background daemon), run
`python scripts/setup_apple_calendar.py` first to pre-authorize.

macOS 14+ (Sonoma): uses requestFullAccessToEventsWithCompletion_ for
read access. Older macOS uses requestAccessToEntityType_completion_.
"""

import asyncio
import datetime
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

# Re-export CalendarEvent so callers import from either calendar module.
from istari.tools.calendar.reader import CalendarEvent  # noqa: E402


class AppleCalendarReader:
    """Read-only EventKit wrapper with the same interface as CalendarReader."""

    def __init__(self) -> None:
        try:
            import EventKit  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "Apple Calendar requires pyobjc-framework-EventKit. "
                "Install with: pip install -e '.[apple]'"
            ) from exc

        self._ek: Any = EventKit
        self._store: Any = EventKit.EKEventStore.alloc().init()

    # ------------------------------------------------------------------
    # Public async API (matches CalendarReader interface)
    # ------------------------------------------------------------------

    async def list_upcoming(
        self,
        days: int = 7,
        max_results: int = 10,
    ) -> list[CalendarEvent]:
        await self._ensure_access_async()
        now = datetime.datetime.now(datetime.UTC)
        end = now + datetime.timedelta(days=days)
        return await asyncio.to_thread(self._list_events_sync, now, end, max_results)

    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[CalendarEvent]:
        await self._ensure_access_async()
        return await asyncio.to_thread(self._search_sync, query, max_results)

    async def get_event(self, event_id: str) -> CalendarEvent | None:
        await self._ensure_access_async()
        return await asyncio.to_thread(self._get_event_sync, event_id)

    # ------------------------------------------------------------------
    # Access / authorization
    # ------------------------------------------------------------------

    async def _ensure_access_async(self) -> None:
        await asyncio.to_thread(self._ensure_access_sync)

    def _ensure_access_sync(self) -> None:
        """Check authorization status; request if undetermined; raise if denied."""
        status = int(
            self._ek.EKEventStore.authorizationStatusForEntityType_(
                self._ek.EKEntityTypeEvent
            )
        )

        # 0 = not determined, 1 = restricted, 2 = denied
        # 3 = authorized (older macOS) / fullAccess (macOS 14+), 4 = writeOnly
        full_access = 3

        if status == full_access:
            return

        if status == 2:  # denied
            raise PermissionError(
                "Calendar access denied. Open System Settings → Privacy & Security "
                "→ Calendars and enable access for the Python process."
            )

        if status == 1:  # restricted
            raise PermissionError(
                "Calendar access is restricted by a device policy."
            )

        # status == 0: not yet determined — request access
        granted = self._request_access_sync()
        if not granted:
            raise PermissionError(
                "Calendar access was not granted. "
                "Run `python scripts/setup_apple_calendar.py` and approve access."
            )

    def _request_access_sync(self) -> bool:
        """Request calendar access; blocks until the OS dialog is resolved."""
        result: list[bool] = [False]
        done = threading.Event()

        def handler(granted: bool, error: Any) -> None:
            result[0] = bool(granted)
            done.set()

        # macOS 14+ (Sonoma): need requestFullAccess for read permission
        if hasattr(self._store, "requestFullAccessToEventsWithCompletion_"):
            self._store.requestFullAccessToEventsWithCompletion_(handler)
        else:
            self._store.requestAccessToEntityType_completion_(
                self._ek.EKEntityTypeEvent, handler
            )

        done.wait(timeout=30)
        logger.info("Apple Calendar access granted: %s", result[0])
        return result[0]

    # ------------------------------------------------------------------
    # Sync fetch methods (run in thread pool via asyncio.to_thread)
    # ------------------------------------------------------------------

    def _list_events_sync(
        self,
        start: datetime.datetime,
        end: datetime.datetime,
        max_results: int,
    ) -> list[CalendarEvent]:
        import Foundation  # type: ignore[import-untyped]

        start_ns = Foundation.NSDate.dateWithTimeIntervalSince1970_(start.timestamp())
        end_ns = Foundation.NSDate.dateWithTimeIntervalSince1970_(end.timestamp())

        calendars = self._store.calendarsForEntityType_(self._ek.EKEntityTypeEvent)
        predicate = self._store.predicateForEventsWithStartDate_endDate_calendars_(
            start_ns, end_ns, calendars
        )
        raw = self._store.eventsMatchingPredicate_(predicate) or []
        raw = sorted(raw, key=lambda e: e.startDate().timeIntervalSince1970())
        return [self._parse_event(e) for e in raw[:max_results]]

    def _search_sync(self, query: str, max_results: int) -> list[CalendarEvent]:
        """Search by fetching a wide window and filtering by title/notes."""
        now = datetime.datetime.now(datetime.UTC)
        start = now - datetime.timedelta(days=30)
        end = now + datetime.timedelta(days=90)

        all_events = self._list_events_sync(start, end, max_results=500)
        q = query.lower()
        matching = [
            e for e in all_events
            if q in (e.summary or "").lower()
            or q in (e.description or "").lower()
            or q in (e.location or "").lower()
        ]
        return matching[:max_results]

    def _get_event_sync(self, event_id: str) -> CalendarEvent | None:
        raw = self._store.calendarItemWithIdentifier_(event_id)
        if raw is None:
            return None
        return self._parse_event(raw)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_event(event: Any) -> CalendarEvent:
        def ns_to_dt(ns_date: Any) -> datetime.datetime | None:
            if ns_date is None:
                return None
            ts = float(ns_date.timeIntervalSince1970())
            return datetime.datetime.fromtimestamp(ts, tz=datetime.UTC)

        organizer = None
        if event.organizer() is not None:
            organizer = str(event.organizer().name() or "")

        return CalendarEvent(
            id=str(event.eventIdentifier() or ""),
            summary=str(event.title() or ""),
            start=ns_to_dt(event.startDate()),
            end=ns_to_dt(event.endDate()),
            location=str(event.location()) if event.location() else "",
            description=str(event.notes()) if event.notes() else "",
            html_link="",
            organizer=organizer or "",
            all_day=bool(event.isAllDay()),
        )
