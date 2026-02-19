"""Tests for GmailReader — all Google API calls are mocked."""

import datetime
from unittest.mock import MagicMock, patch

import pytest

from istari.tools.gmail.reader import EmailSummary, GmailReader, ThreadDetail


@pytest.fixture()
def mock_service():
    """Return a mock Gmail API service."""
    return MagicMock()


@pytest.fixture()
def reader(tmp_path, mock_service):
    """Create a GmailReader with a fake token file and mocked service."""
    token_file = tmp_path / "token.json"
    # Minimal valid token JSON (will be mocked anyway)
    token_file.write_text(
        '{"token": "fake", "refresh_token": "fake",'
        ' "client_id": "x", "client_secret": "y"}'
    )
    with (
        patch("istari.tools.gmail.reader.Credentials.from_authorized_user_file") as mock_creds_cls,
        patch("istari.tools.gmail.reader.build", return_value=mock_service),
    ):
        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds_cls.return_value = mock_creds
        r = GmailReader(str(token_file))
    return r


def _make_message(msg_id: str, thread_id: str, subject: str, sender: str, snippet: str) -> dict:
    return {
        "id": msg_id,
        "threadId": thread_id,
        "snippet": snippet,
        "payload": {
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
                {"name": "Date", "value": "Mon, 10 Feb 2025 09:00:00 +0000"},
            ]
        },
    }


@pytest.mark.asyncio
async def test_list_unread(reader, mock_service):
    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "m1"}, {"id": "m2"}]
    }
    mock_service.users().messages().get().execute.side_effect = [
        _make_message("m1", "t1", "Hello", "alice@test.com", "Hi there"),
        _make_message("m2", "t2", "Meeting", "bob@test.com", "Let's meet"),
    ]

    results = await reader.list_unread(max_results=5)

    assert len(results) == 2
    assert isinstance(results[0], EmailSummary)
    assert results[0].id == "m1"
    assert results[0].subject == "Hello"
    assert results[0].sender == "alice@test.com"
    assert results[1].id == "m2"


@pytest.mark.asyncio
async def test_list_unread_empty(reader, mock_service):
    mock_service.users().messages().list().execute.return_value = {"messages": []}

    results = await reader.list_unread()
    assert results == []


@pytest.mark.asyncio
async def test_search(reader, mock_service):
    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "m3"}]
    }
    mock_service.users().messages().get().execute.return_value = _make_message(
        "m3", "t3", "Invoice", "billing@test.com", "Your invoice"
    )

    results = await reader.search("from:billing", max_results=10)

    assert len(results) == 1
    assert results[0].subject == "Invoice"


@pytest.mark.asyncio
async def test_get_thread(reader, mock_service):
    import base64

    body_data = base64.urlsafe_b64encode(b"Hello, how are you?").decode()
    mock_service.users().threads().get().execute.return_value = {
        "id": "t1",
        "messages": [
            {
                "id": "m1",
                "payload": {
                    "mimeType": "text/plain",
                    "headers": [
                        {"name": "Subject", "value": "Greetings"},
                        {"name": "From", "value": "alice@test.com"},
                        {"name": "Date", "value": "Mon, 10 Feb 2025 09:00:00 +0000"},
                    ],
                    "body": {"data": body_data},
                },
            }
        ],
    }

    result = await reader.get_thread("t1")

    assert isinstance(result, ThreadDetail)
    assert result.thread_id == "t1"
    assert result.subject == "Greetings"
    assert len(result.messages) == 1
    assert result.messages[0].body == "Hello, how are you?"


def test_token_not_found():
    with pytest.raises(FileNotFoundError, match="Gmail token not found"):
        GmailReader("/nonexistent/token.json")


def test_parse_date():
    dt = GmailReader._parse_date("Mon, 10 Feb 2025 09:00:00 +0000")
    assert dt is not None
    assert dt.year == 2025
    assert dt.month == 2
    assert dt.tzinfo == datetime.UTC


def test_parse_date_none():
    assert GmailReader._parse_date(None) is None


def test_parse_date_invalid():
    assert GmailReader._parse_date("not a date") is None
