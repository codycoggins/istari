"""Tests for chat agent — LLM-based intent classification and graph routing."""

from unittest.mock import AsyncMock, patch

import pytest
from tests.fixtures.llm_responses import mock_chat_response, mock_classification_response

from istari.agents.chat import Intent, build_chat_graph


@pytest.fixture
def _mock_classify():
    """Fixture factory: patch LLM completion to return a given intent + content."""

    def _make(intent: str, extracted_content: str = ""):
        resp = mock_classification_response(intent, extracted_content)
        return patch(
            "istari.llm.router.completion",
            new_callable=AsyncMock,
            return_value=resp,
        )

    return _make


@pytest.fixture
def graph():
    return build_chat_graph()


# --- TODO capture ---


class TestTodoCapture:
    async def test_todo_basic(self, graph, _mock_classify):
        with _mock_classify("todo_capture", "Review the PR"):
            result = await graph.ainvoke({"user_message": "TODO: review the PR"})
        assert result["intent"] == Intent.TODO_CAPTURE.value
        assert result["extracted_content"] == "Review the PR"
        assert "Review the PR" in result["response"]

    async def test_todo_normalization(self, graph, _mock_classify):
        with _mock_classify("todo_capture", "Pay the condo fee"):
            result = await graph.ainvoke(
                {"user_message": "add a todo for taking care of the condo fee payment"}
            )
        assert result["intent"] == Intent.TODO_CAPTURE.value
        assert result["extracted_content"] == "Pay the condo fee"

    async def test_remind_me_to(self, graph, _mock_classify):
        with _mock_classify("todo_capture", "Call the dentist"):
            result = await graph.ainvoke({"user_message": "remind me to call the dentist"})
        assert result["intent"] == Intent.TODO_CAPTURE.value
        assert result["extracted_content"] == "Call the dentist"

    async def test_need_to(self, graph, _mock_classify):
        with _mock_classify("todo_capture", "Finish the slides"):
            result = await graph.ainvoke({"user_message": "I need to finish the slides"})
        assert result["intent"] == Intent.TODO_CAPTURE.value

    async def test_dont_forget(self, graph, _mock_classify):
        with _mock_classify("todo_capture", "Water the plants"):
            result = await graph.ainvoke({"user_message": "don't forget to water the plants"})
        assert result["intent"] == Intent.TODO_CAPTURE.value


# --- Memory write ---


class TestMemoryWrite:
    async def test_remember_that(self, graph, _mock_classify):
        with _mock_classify("memory_write", "I prefer mornings"):
            result = await graph.ainvoke(
                {"user_message": "remember that I prefer mornings"}
            )
        assert result["intent"] == Intent.MEMORY_WRITE.value
        assert result["extracted_content"] == "I prefer mornings"
        assert "noted" in result["response"].lower() or "remember" in result["response"].lower()

    async def test_note_that(self, graph, _mock_classify):
        with _mock_classify("memory_write", "The deadline is Friday"):
            result = await graph.ainvoke(
                {"user_message": "note that the deadline is Friday"}
            )
        assert result["intent"] == Intent.MEMORY_WRITE.value

    async def test_preference(self, graph, _mock_classify):
        with _mock_classify("memory_write", "I prefer dark mode"):
            result = await graph.ainvoke({"user_message": "I prefer dark mode"})
        assert result["intent"] == Intent.MEMORY_WRITE.value

    async def test_fyi(self, graph, _mock_classify):
        with _mock_classify("memory_write", "The server IP changed to 10.0.0.1"):
            result = await graph.ainvoke(
                {"user_message": "FYI, the server IP changed to 10.0.0.1"}
            )
        assert result["intent"] == Intent.MEMORY_WRITE.value
        assert "server IP" in result["extracted_content"]

    async def test_keep_in_mind(self, graph, _mock_classify):
        with _mock_classify("memory_write", "I'm off on Fridays"):
            result = await graph.ainvoke(
                {"user_message": "keep in mind that I'm off on Fridays"}
            )
        assert result["intent"] == Intent.MEMORY_WRITE.value
        assert "off on Fridays" in result["extracted_content"]


# --- Prioritize ---


class TestPrioritize:
    async def test_what_should_i_work_on(self, graph, _mock_classify):
        with _mock_classify("prioritize"):
            result = await graph.ainvoke({"user_message": "What should I work on?"})
        assert result["intent"] == Intent.PRIORITIZE.value
        assert result["response"] == "__PRIORITIZE__"

    async def test_what_should_i_do(self, graph, _mock_classify):
        with _mock_classify("prioritize"):
            result = await graph.ainvoke({"user_message": "what should I do?"})
        assert result["intent"] == Intent.PRIORITIZE.value

    async def test_show_priorities(self, graph, _mock_classify):
        with _mock_classify("prioritize"):
            result = await graph.ainvoke({"user_message": "show my priorities"})
        assert result["intent"] == Intent.PRIORITIZE.value

    async def test_what_should_i_focus_on(self, graph, _mock_classify):
        with _mock_classify("prioritize"):
            result = await graph.ainvoke({"user_message": "what should I focus on?"})
        assert result["intent"] == Intent.PRIORITIZE.value


# --- General chat ---


class TestChat:
    async def test_greeting(self, graph, _mock_classify):
        with _mock_classify("chat"):
            result = await graph.ainvoke({"user_message": "Hello!"})
        assert result["intent"] == Intent.CHAT.value
        assert result["response"] == "__LLM_CALL__"

    async def test_general_question(self, graph, _mock_classify):
        with _mock_classify("chat"):
            result = await graph.ainvoke(
                {"user_message": "What is the capital of France?"}
            )
        assert result["intent"] == Intent.CHAT.value

    async def test_general_conversation(self, graph, _mock_classify):
        with _mock_classify("chat"):
            result = await graph.ainvoke(
                {"user_message": "Tell me about quantum computing"}
            )
        assert result["intent"] == Intent.CHAT.value


# --- Sensitive content ---


class TestSensitiveContent:
    async def test_email_flagged_sensitive(self, graph, _mock_classify):
        with _mock_classify("chat"):
            result = await graph.ainvoke(
                {"user_message": "email john@example.com about the meeting"}
            )
        assert result["is_sensitive"] is True


# --- Error handling / fallbacks ---


class TestClassifyFallbacks:
    async def test_malformed_json_falls_back_to_chat(self, graph):
        """If LLM returns non-JSON, fall back to chat intent."""
        bad_resp = mock_chat_response("I think this is a todo about groceries")
        with patch("istari.llm.router.completion", new_callable=AsyncMock, return_value=bad_resp):
            result = await graph.ainvoke({"user_message": "buy milk maybe?"})
        assert result["intent"] == Intent.CHAT.value
        assert result["extracted_content"] == ""

    async def test_invalid_intent_falls_back_to_chat(self, graph):
        """If LLM returns an unknown intent, fall back to chat."""
        bad_resp = mock_classification_response("unknown_intent", "something")
        with patch("istari.llm.router.completion", new_callable=AsyncMock, return_value=bad_resp):
            result = await graph.ainvoke({"user_message": "do something weird"})
        assert result["intent"] == Intent.CHAT.value

    async def test_llm_exception_falls_back_to_chat(self, graph):
        """If the LLM call raises an exception, fall back to chat."""
        with patch(
            "istari.llm.router.completion",
            new_callable=AsyncMock,
            side_effect=RuntimeError("connection failed"),
        ):
            result = await graph.ainvoke({"user_message": "add a todo for groceries"})
        assert result["intent"] == Intent.CHAT.value
        assert result["extracted_content"] == ""

    async def test_empty_message_falls_back_to_chat(self, graph, _mock_classify):
        with _mock_classify("chat"):
            result = await graph.ainvoke({"user_message": ""})
        assert result["intent"] == Intent.CHAT.value
