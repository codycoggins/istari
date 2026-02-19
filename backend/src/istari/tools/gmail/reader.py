"""Gmail reader tool — search inbox, list unread, fetch threads. Read-only."""

import asyncio
import base64
import datetime
import email.utils
import logging
from dataclasses import dataclass, field
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


@dataclass
class EmailSummary:
    id: str
    thread_id: str
    subject: str
    sender: str
    snippet: str
    date: datetime.datetime | None


@dataclass
class ThreadMessage:
    id: str
    sender: str
    subject: str
    date: datetime.datetime | None
    body: str


@dataclass
class ThreadDetail:
    thread_id: str
    subject: str
    messages: list[ThreadMessage] = field(default_factory=list)


class GmailReader:
    """Read-only Gmail API wrapper. Requires a saved OAuth token."""

    def __init__(self, token_path: str) -> None:
        path = Path(token_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Gmail token not found at {path}. Run: python scripts/setup_gmail.py"
            )
        creds = Credentials.from_authorized_user_file(str(path))
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            path.write_text(creds.to_json())
        self._service = build("gmail", "v1", credentials=creds)

    def _list_messages_sync(self, query: str, max_results: int) -> list[EmailSummary]:
        resp = (
            self._service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        messages = resp.get("messages", [])
        if not messages:
            return []

        results: list[EmailSummary] = []
        for msg_ref in messages:
            msg = (
                self._service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="metadata",
                     metadataHeaders=["Subject", "From", "Date"])
                .execute()
            )
            results.append(self._parse_summary(msg))
        return results

    def _get_thread_sync(self, thread_id: str) -> ThreadDetail:
        thread = (
            self._service.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )
        messages: list[ThreadMessage] = []
        subject = ""
        for msg in thread.get("messages", []):
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            if not subject:
                subject = headers.get("Subject", "(no subject)")
            date = self._parse_date(headers.get("Date"))
            body = self._extract_body(msg.get("payload", {}))
            messages.append(ThreadMessage(
                id=msg["id"],
                sender=headers.get("From", ""),
                subject=headers.get("Subject", ""),
                date=date,
                body=body,
            ))
        return ThreadDetail(thread_id=thread_id, subject=subject, messages=messages)

    async def list_unread(self, max_results: int = 20) -> list[EmailSummary]:
        return await asyncio.to_thread(self._list_messages_sync, "is:unread", max_results)

    async def search(self, query: str, max_results: int = 20) -> list[EmailSummary]:
        return await asyncio.to_thread(self._list_messages_sync, query, max_results)

    async def get_thread(self, thread_id: str) -> ThreadDetail:
        return await asyncio.to_thread(self._get_thread_sync, thread_id)

    @staticmethod
    def _parse_summary(msg: dict) -> EmailSummary:
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        return EmailSummary(
            id=msg["id"],
            thread_id=msg.get("threadId", ""),
            subject=headers.get("Subject", "(no subject)"),
            sender=headers.get("From", ""),
            snippet=msg.get("snippet", ""),
            date=GmailReader._parse_date(headers.get("Date")),
        )

    @staticmethod
    def _parse_date(date_str: str | None) -> datetime.datetime | None:
        if not date_str:
            return None
        try:
            parsed = email.utils.parsedate_to_datetime(date_str)
            return parsed.astimezone(datetime.UTC)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _extract_body(payload: dict) -> str:
        """Extract plain text body from a message payload, handling multipart."""
        mime = payload.get("mimeType", "")
        if mime == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        if mime.startswith("multipart/"):
            for part in payload.get("parts", []):
                text = GmailReader._extract_body(part)
                if text:
                    return text
        return ""
