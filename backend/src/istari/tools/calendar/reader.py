"""Calendar reader tool — list events, search, check free/busy. Read-only."""

import asyncio
import datetime
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


@dataclass
class CalendarEvent:
    id: str
    summary: str
    start: datetime.datetime | datetime.date | None
    end: datetime.datetime | datetime.date | None
    location: str
    description: str
    html_link: str
    organizer: str
    all_day: bool


@dataclass
class CalendarEventList:
    events: list[CalendarEvent] = field(default_factory=list)


class CalendarReader:
    """Read-only Google Calendar API wrapper. Requires a saved OAuth token."""

    SCOPES: ClassVar[list[str]] = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(self, token_path: str) -> None:
        path = Path(token_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Calendar token not found at {path}. "
                "Run: python scripts/setup_calendar.py"
            )
        creds = Credentials.from_authorized_user_file(str(path), self.SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            path.write_text(creds.to_json())
        self._service = build("calendar", "v3", credentials=creds)

    def _list_events_sync(
        self,
        *,
        query: str | None = None,
        time_min: datetime.datetime | None = None,
        time_max: datetime.datetime | None = None,
        max_results: int = 10,
    ) -> list[CalendarEvent]:
        now = datetime.datetime.now(datetime.UTC)
        params: dict = {
            "calendarId": "primary",
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
            "timeMin": (time_min or now).isoformat(),
        }
        if query:
            params["q"] = query
        if time_max:
            params["timeMax"] = time_max.isoformat()

        resp = self._service.events().list(**params).execute()
        return [self._parse_event(e) for e in resp.get("items", [])]

    def _get_event_sync(self, event_id: str) -> CalendarEvent:
        event = (
            self._service.events()
            .get(calendarId="primary", eventId=event_id)
            .execute()
        )
        return self._parse_event(event)

    async def list_upcoming(
        self, days: int = 7, max_results: int = 10
    ) -> list[CalendarEvent]:
        """Return events starting within the next `days` days."""
        now = datetime.datetime.now(datetime.UTC)
        time_max = now + datetime.timedelta(days=days)
        return await asyncio.to_thread(
            self._list_events_sync,
            time_min=now,
            time_max=time_max,
            max_results=max_results,
        )

    async def search(self, query: str, max_results: int = 10) -> list[CalendarEvent]:
        """Search events by text query (searches title, description, location)."""
        now = datetime.datetime.now(datetime.UTC)
        return await asyncio.to_thread(
            self._list_events_sync,
            query=query,
            time_min=now,
            max_results=max_results,
        )

    async def get_event(self, event_id: str) -> CalendarEvent:
        """Fetch full details of a single event by ID."""
        return await asyncio.to_thread(self._get_event_sync, event_id)

    @staticmethod
    def _parse_event(event: dict) -> CalendarEvent:
        start_raw = event.get("start", {})
        end_raw = event.get("end", {})
        all_day = "date" in start_raw and "dateTime" not in start_raw

        return CalendarEvent(
            id=event.get("id", ""),
            summary=event.get("summary", "(no title)"),
            start=CalendarReader._parse_dt(start_raw),
            end=CalendarReader._parse_dt(end_raw),
            location=event.get("location", ""),
            description=event.get("description", ""),
            html_link=event.get("htmlLink", ""),
            organizer=event.get("organizer", {}).get("email", ""),
            all_day=all_day,
        )

    @staticmethod
    def _parse_dt(
        dt_dict: dict,
    ) -> datetime.datetime | datetime.date | None:
        if not dt_dict:
            return None
        if "dateTime" in dt_dict:
            try:
                return datetime.datetime.fromisoformat(dt_dict["dateTime"])
            except (ValueError, TypeError):
                return None
        if "date" in dt_dict:
            try:
                return datetime.date.fromisoformat(dt_dict["date"])
            except (ValueError, TypeError):
                return None
        return None
