"""Tests for agent tool functions and the ReAct agent loop."""

import datetime
import json
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from istari.agents.tools.base import AgentContext, normalize_status
from istari.agents.tools.calendar import make_calendar_tools
from istari.agents.tools.gmail import make_gmail_tools
from istari.agents.tools.memory import make_memory_tools
from istari.agents.tools.todo import make_todo_tools
from istari.models.todo import TodoStatus
from istari.tools.todo.manager import TodoManager


@contextmanager
def _patch_llm():
    client = MagicMock()
    create = AsyncMock()
    client.chat.completions.create = create
    with patch("istari.llm.router.AsyncOpenAI", return_value=client):
        yield create

# ---------------------------------------------------------------------------
# normalize_status
# ---------------------------------------------------------------------------

class TestNormalizeStatus:
    def test_passthrough_valid(self):
        assert normalize_status("complete") == "complete"
        assert normalize_status("in_progress") == "in_progress"
        assert normalize_status("blocked") == "blocked"
        assert normalize_status("deferred") == "deferred"
        assert normalize_status("open") == "open"

    def test_done_maps_to_complete(self):
        assert normalize_status("done") == "complete"

    def test_finished_maps_to_complete(self):
        assert normalize_status("finished") == "complete"

    def test_started_maps_to_in_progress(self):
        assert normalize_status("started") == "in_progress"

    def test_stuck_maps_to_blocked(self):
        assert normalize_status("stuck") == "blocked"

    def test_later_maps_to_deferred(self):
        assert normalize_status("later") == "deferred"

    def test_case_insensitive(self):
        assert normalize_status("Done") == "complete"
        assert normalize_status("FINISHED") == "complete"

    def test_strips_whitespace(self):
        assert normalize_status("  done  ") == "complete"

    def test_unknown_passthrough(self):
        assert normalize_status("whatever") == "whatever"


# ---------------------------------------------------------------------------
# Todo tools
# ---------------------------------------------------------------------------

class TestCreateTodosTool:
    async def test_creates_single_todo(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["create_todos"].fn(titles=["Buy groceries"])

        assert "Buy groceries" in result
        assert ctx.todo_created is True

        mgr = TodoManager(db_session)
        todos = await mgr.list_open()
        assert any(t.title == "Buy groceries" for t in todos)

    async def test_creates_multiple_todos(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        titles = [
            "Eat breakfast on Monday",
            "Eat breakfast on Tuesday",
            "Eat breakfast on Wednesday",
        ]
        result = await tools["create_todos"].fn(titles=titles)

        assert "3" in result
        assert ctx.todo_created is True

        mgr = TodoManager(db_session)
        todos = await mgr.list_open()
        created_titles = {t.title for t in todos}
        for title in titles:
            assert title in created_titles

    async def test_create_trims_whitespace(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        await tools["create_todos"].fn(titles=["  Fix the bug  "])

        mgr = TodoManager(db_session)
        todos = await mgr.list_open()
        assert any(t.title == "Fix the bug" for t in todos)


class TestUpdateTodoStatusTool:
    async def test_update_by_numeric_id(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Pay bills")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["update_todo_status"].fn(
            query=str(todo.id), status="complete"
        )

        assert "complete" in result
        assert ctx.todo_updated is True

        updated = await mgr.get(todo.id)
        assert updated.status == TodoStatus.COMPLETE

    async def test_update_by_pattern_single_match(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("Call the dentist")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["update_todo_status"].fn(query="dentist", status="complete")

        assert "complete" in result
        assert ctx.todo_updated is True

    async def test_update_by_pattern_bulk(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("Eat breakfast on Monday")
        await mgr.create("Eat breakfast on Tuesday")
        await mgr.create("Eat breakfast on Wednesday")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["update_todo_status"].fn(
            query="eat breakfast", status="complete"
        )

        assert "3" in result
        assert ctx.todo_updated is True

        todos = await mgr.list_visible()
        breakfast_todos = [t for t in todos if "breakfast" in t.title.lower()]
        assert all(t.status == TodoStatus.COMPLETE for t in breakfast_todos)

    async def test_update_with_synonym_done(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("Review PR")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["update_todo_status"].fn(query="Review PR", status="done")

        assert "complete" in result
        assert ctx.todo_updated is True

    async def test_update_no_match_returns_message(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["update_todo_status"].fn(
            query="nonexistent task xyz", status="complete"
        )

        assert "No TODOs found" in result
        assert ctx.todo_updated is False

    async def test_update_invalid_status_returns_message(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["update_todo_status"].fn(
            query="anything", status="banana"
        )

        assert "not a valid status" in result.lower() or "valid" in result.lower()
        assert ctx.todo_updated is False


class TestListTodosTool:
    async def test_returns_open_todos_by_default(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("Task A")
        await mgr.create("Task B")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["list_todos"].fn(filter="open")

        assert "Task A" in result
        assert "Task B" in result

    async def test_returns_message_when_empty(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["list_todos"].fn(filter="open")

        assert "No TODOs" in result

    async def test_complete_filter(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Done task")
        await mgr.set_status(todo.id, TodoStatus.COMPLETE)
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["list_todos"].fn(filter="complete")

        assert "Done task" in result


class TestGetPrioritiesTool:
    async def test_returns_top_todos(self, db_session):
        mgr = TodoManager(db_session)
        await mgr.create("High priority task", priority=1)
        await mgr.create("Low priority task", priority=5)
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["get_priorities"].fn()

        assert "High priority task" in result

    async def test_no_todos_returns_message(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["get_priorities"].fn()

        assert "No active" in result


# ---------------------------------------------------------------------------
# Memory tools
# ---------------------------------------------------------------------------

class TestTodayFocusTools:
    async def test_set_today_focus_adds_task(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Write report")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["set_today_focus"].fn(query=str(todo.id), focus=True)

        assert "Write report" in result
        assert "Added" in result
        assert ctx.todo_updated is True

        updated = await mgr.get(todo.id)
        import datetime
        assert updated.today_date == datetime.date.today()

    async def test_set_today_focus_removes_task(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Clean desk")
        await mgr.set_today(todo.id, True)
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["set_today_focus"].fn(query=str(todo.id), focus=False)

        assert "Removed" in result
        assert ctx.todo_updated is True

        updated = await mgr.get(todo.id)
        assert updated.today_date is None

    async def test_get_today_focus_empty(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["get_today_focus"].fn()

        assert "haven't set" in result

    async def test_get_today_focus_shows_tasks(self, db_session):
        mgr = TodoManager(db_session)
        todo = await mgr.create("Review PRs")
        await mgr.set_today(todo.id, True)
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_todo_tools(db_session, ctx)}
        result = await tools["get_today_focus"].fn()

        assert "Review PRs" in result
        assert "1/5" in result or "Today's focus" in result


class TestMemoryTools:
    async def test_remember_stores_and_sets_flag(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_memory_tools(db_session, ctx)}
        result = await tools["remember"].fn(fact="I prefer dark mode")

        assert "dark mode" in result
        assert ctx.memory_created is True

    async def test_search_memory_finds_stored(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_memory_tools(db_session, ctx)}
        await tools["remember"].fn(fact="Favourite colour is blue")

        result = await tools["search_memory"].fn(query="colour")
        assert "blue" in result

    async def test_search_memory_no_match(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_memory_tools(db_session, ctx)}
        result = await tools["search_memory"].fn(query="nonexistent xyz")

        assert "No memories" in result


# ---------------------------------------------------------------------------
# Gmail tools
# ---------------------------------------------------------------------------

class TestGmailTools:
    def _mock_reader(self, emails):
        """Build a mock GmailReader that returns the given EmailSummary list."""
        reader = MagicMock()
        reader.list_unread = AsyncMock(return_value=emails)
        reader.search = AsyncMock(return_value=emails)
        return reader

    def _make_email(self, subject="Test Subject", sender="test@example.com",
                    snippet="snippet text", thread_id="thread123"):
        from istari.tools.gmail.reader import EmailSummary
        return EmailSummary(
            id="msg1", thread_id=thread_id, subject=subject,
            sender=sender, snippet=snippet, date=datetime.datetime(2024, 1, 1),
        )

    async def test_check_email_with_query_and_max_results(self, monkeypatch):
        """LLM passes max_results — must not raise TypeError."""
        email = self._make_email()
        mock_reader = self._mock_reader([email])

        monkeypatch.setattr("istari.agents.tools.gmail.GmailReader", lambda token: mock_reader)
        monkeypatch.setattr("istari.agents.tools.gmail.settings.gmail_token_path", "/fake/token")

        tools = {t.name: t for t in make_gmail_tools()}
        # This is the exact call the LLM made that caused the TypeError
        result = await tools["check_email"].fn(query="SYC", max_results=5)

        mock_reader.search.assert_called_once_with("SYC", max_results=5)
        assert "Test Subject" in result

    async def test_check_email_no_args_uses_unread(self, monkeypatch):
        email = self._make_email()
        mock_reader = self._mock_reader([email])

        monkeypatch.setattr("istari.agents.tools.gmail.GmailReader", lambda token: mock_reader)
        monkeypatch.setattr("istari.agents.tools.gmail.settings.gmail_token_path", "/fake/token")

        tools = {t.name: t for t in make_gmail_tools()}
        result = await tools["check_email"].fn()

        mock_reader.list_unread.assert_called_once()
        assert "Test Subject" in result

    async def test_check_email_result_contains_link(self, monkeypatch):
        email = self._make_email(thread_id="abc123")
        mock_reader = self._mock_reader([email])

        monkeypatch.setattr("istari.agents.tools.gmail.GmailReader", lambda token: mock_reader)
        monkeypatch.setattr("istari.agents.tools.gmail.settings.gmail_token_path", "/fake/token")

        tools = {t.name: t for t in make_gmail_tools()}
        result = await tools["check_email"].fn()

        assert "https://mail.google.com/mail/u/0/#all/abc123" in result

    def test_check_email_schema_includes_max_results(self):
        """Tool schema must declare max_results so the LLM knows it's valid."""
        tools = {t.name: t for t in make_gmail_tools()}
        schema = tools["check_email"].to_openai_schema()
        props = schema["function"]["parameters"]["properties"]
        assert "max_results" in props


# ---------------------------------------------------------------------------
# Calendar tools
# ---------------------------------------------------------------------------

class TestCalendarTools:
    def _make_event(self, summary="Team standup", html_link="", event_id="ev1"):
        from istari.tools.calendar.reader import CalendarEvent
        return CalendarEvent(
            id=event_id,
            summary=summary,
            start=datetime.datetime(2026, 3, 10, 9, 0, tzinfo=datetime.UTC),
            end=datetime.datetime(2026, 3, 10, 9, 30, tzinfo=datetime.UTC),
            location="",
            description="",
            html_link=html_link,
            organizer="",
            all_day=False,
        )

    def _mock_reader(self, events):
        reader = MagicMock()
        reader.list_upcoming = AsyncMock(return_value=events)
        reader.search = AsyncMock(return_value=events)
        return reader

    async def test_check_calendar_result_contains_link(self, monkeypatch):
        """html_link from CalendarEvent must appear as a markdown link in output."""
        event = self._make_event(
            html_link="https://calendar.google.com/event?eid=ev1"
        )
        mock_reader = self._mock_reader([event])

        monkeypatch.setattr(
            "istari.agents.tools.calendar.CalendarReader", lambda token: mock_reader
        )
        monkeypatch.setattr(
            "istari.agents.tools.calendar.settings.calendar_token_path", "/fake/token"
        )
        monkeypatch.setattr(
            "istari.agents.tools.calendar.settings.calendar_backend", "google"
        )
        monkeypatch.setattr(
            "istari.agents.tools.calendar.settings.calendar_max_results", 10
        )

        tools = {t.name: t for t in make_calendar_tools()}
        result = await tools["check_calendar"].fn()

        assert "https://calendar.google.com/event?eid=ev1" in result
        assert "[Team standup]" in result

    async def test_check_calendar_no_link_falls_back_to_plain_text(self, monkeypatch):
        """When html_link is empty the summary is shown without a link."""
        event = self._make_event(html_link="")
        mock_reader = self._mock_reader([event])

        monkeypatch.setattr(
            "istari.agents.tools.calendar.CalendarReader", lambda token: mock_reader
        )
        monkeypatch.setattr(
            "istari.agents.tools.calendar.settings.calendar_token_path", "/fake/token"
        )
        monkeypatch.setattr(
            "istari.agents.tools.calendar.settings.calendar_backend", "google"
        )
        monkeypatch.setattr(
            "istari.agents.tools.calendar.settings.calendar_max_results", 10
        )

        tools = {t.name: t for t in make_calendar_tools()}
        result = await tools["check_calendar"].fn()

        assert "Team standup" in result
        assert "](http" not in result  # no markdown link


# ---------------------------------------------------------------------------
# Tool schema format
# ---------------------------------------------------------------------------

class TestToolSchemas:
    def test_all_tools_have_valid_openai_schema(self, db_session):
        from istari.agents.chat import build_tools

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)
        for tool in tools:
            schema = tool.to_openai_schema()
            assert schema["type"] == "function"
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_no_duplicate_tool_names(self, db_session):
        from istari.agents.chat import build_tools

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)
        names = [t.name for t in tools]
        assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# run_agent — mocked LLM
# ---------------------------------------------------------------------------

def _make_tool_call_response(tool_name: str, arguments: dict, call_id: str = "call_1"):
    """Build a mock LiteLLM response that requests a tool call."""
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(arguments)

    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]

    choice = MagicMock()
    choice.message = msg

    response = MagicMock()
    response.choices = [choice]
    return response


def _make_text_response(content: str):
    """Build a mock LiteLLM response with a final text reply."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None

    choice = MagicMock()
    choice.message = msg

    response = MagicMock()
    response.choices = [choice]
    return response


class TestRunAgent:
    async def test_direct_response_no_tools(self, db_session):
        from istari.agents.chat import build_tools, run_agent

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        with _patch_llm() as mock_llm:
            mock_llm.return_value = _make_text_response("Hello, how can I help?")
            result = await run_agent("Hi there", [], tools, system_prompt="You are Istari.")

        assert result == "Hello, how can I help?"

    async def test_create_todos_via_tool_call(self, db_session):
        from istari.agents.chat import build_tools, run_agent

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        tool_resp = _make_tool_call_response(
            "create_todos", {"titles": ["Buy milk", "Walk the dog"]}
        )
        final_resp = _make_text_response("Done! I've added 2 TODOs for you.")

        with _patch_llm() as mock_llm:
            mock_llm.side_effect = [tool_resp, final_resp]
            await run_agent(
                "Add todos: buy milk and walk the dog", [], tools,
                system_prompt="You are Istari.",
            )

        assert ctx.todo_created is True
        mgr = TodoManager(db_session)
        open_todos = await mgr.list_open()
        titles = {t.title for t in open_todos}
        assert "Buy milk" in titles
        assert "Walk the dog" in titles

    async def test_llm_error_returns_friendly_message(self, db_session):
        from istari.agents.chat import build_tools, run_agent

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        with _patch_llm() as mock_llm:
            mock_llm.side_effect = Exception("API unavailable")
            result = await run_agent(
                "What should I do?", [], tools, system_prompt="You are Istari.",
            )

        assert "trouble" in result.lower() or "try again" in result.lower()

    async def test_system_prompt_passed_to_llm(self, db_session):
        from istari.agents.chat import build_tools, run_agent

        ctx = AgentContext()
        tools = build_tools(db_session, ctx)

        with _patch_llm() as mock_llm:
            mock_llm.return_value = _make_text_response("Got it!")
            await run_agent("Hi", [], tools, system_prompt="The user's name is Cody.")

        call_messages = mock_llm.call_args.kwargs["messages"]
        system_msg = call_messages[0]
        assert "Cody" in system_msg["content"]
