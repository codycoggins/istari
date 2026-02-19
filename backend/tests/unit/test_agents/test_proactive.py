"""Tests for the proactive agent graph nodes."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from istari.agents.proactive import (
    ProactiveState,
    check_staleness_node,
    queue_notifications_node,
    scan_gmail_node,
    summarize_node,
)


@pytest.mark.asyncio
async def test_scan_gmail_node_success():
    from istari.tools.gmail.reader import EmailSummary

    mock_emails = [
        EmailSummary(
            id="m1",
            thread_id="t1",
            subject="Test",
            sender="a@b.com",
            snippet="Hello",
            date=datetime.datetime(2025, 2, 10, tzinfo=datetime.UTC),
        )
    ]

    with patch("istari.tools.gmail.reader.GmailReader") as mock_cls:
        instance = MagicMock()
        instance.list_unread = AsyncMock(return_value=mock_emails)
        mock_cls.return_value = instance

        state: ProactiveState = {"task_type": "gmail_digest", "gmail_token_path": "fake.json"}
        result = await scan_gmail_node(state)

    assert len(result["emails"]) == 1
    assert result["emails"][0]["subject"] == "Test"


@pytest.mark.asyncio
async def test_scan_gmail_node_token_not_found():
    with patch("istari.tools.gmail.reader.GmailReader", side_effect=FileNotFoundError):
        state: ProactiveState = {"task_type": "gmail_digest"}
        result = await scan_gmail_node(state)

    assert result["emails"] == []


@pytest.mark.asyncio
async def test_check_staleness_node_with_session():
    mock_todo = MagicMock()
    mock_todo.id = 1
    mock_todo.title = "Old task"
    mock_todo.status.value = "open"
    mock_todo.updated_at = datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)

    with patch("istari.tools.todo.manager.TodoManager") as mock_mgr_cls:
        instance = MagicMock()
        instance.get_stale = AsyncMock(return_value=[mock_todo])
        mock_mgr_cls.return_value = instance

        state: ProactiveState = {
            "task_type": "staleness_only", "db_session": MagicMock(),
            "stale_todo_days": 3,
        }
        result = await check_staleness_node(state)

    assert len(result["stale_todos"]) == 1
    assert result["stale_todos"][0]["title"] == "Old task"


@pytest.mark.asyncio
async def test_check_staleness_node_no_session():
    state: ProactiveState = {"task_type": "staleness_only"}
    result = await check_staleness_node(state)
    assert result["stale_todos"] == []


@pytest.mark.asyncio
async def test_summarize_node_no_content():
    state: ProactiveState = {"emails": [], "stale_todos": []}
    result = await summarize_node(state)
    assert result["digest_text"] == "No new emails or stale TODOs to report."


@pytest.mark.asyncio
async def test_summarize_node_with_emails():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "You have 1 urgent email."

    with patch("istari.llm.router.completion", new_callable=AsyncMock, return_value=mock_response):
        state: ProactiveState = {
            "emails": [{"subject": "Urgent", "sender": "boss@co.com", "snippet": "Need ASAP"}],
            "stale_todos": [],
        }
        result = await summarize_node(state)

    assert result["digest_text"] == "You have 1 urgent email."


@pytest.mark.asyncio
async def test_summarize_node_llm_failure():
    with patch(
        "istari.llm.router.completion",
        new_callable=AsyncMock, side_effect=RuntimeError("LLM down"),
    ):
        state: ProactiveState = {
            "emails": [{"subject": "Test", "sender": "a@b.com", "snippet": "Hi"}],
            "stale_todos": [],
        }
        result = await summarize_node(state)

    # Falls back to raw content
    assert "Test" in result["digest_text"]


def test_queue_notifications_node_with_digest():
    state: ProactiveState = {
        "task_type": "gmail_digest",
        "digest_text": "You have 3 unread emails.",
    }
    result = queue_notifications_node(state)
    assert len(result["notifications"]) == 1
    assert result["notifications"][0]["type"] == "gmail_digest"
    assert "3 unread" in result["notifications"][0]["content"]


def test_queue_notifications_node_empty():
    state: ProactiveState = {
        "task_type": "gmail_digest",
        "digest_text": "No new emails or stale TODOs to report.",
    }
    result = queue_notifications_node(state)
    assert result["notifications"] == []


def test_queue_notifications_node_staleness():
    state: ProactiveState = {
        "task_type": "staleness_only",
        "digest_text": "2 stale TODOs need attention.",
    }
    result = queue_notifications_node(state)
    assert result["notifications"][0]["type"] == "todo_staleness"
