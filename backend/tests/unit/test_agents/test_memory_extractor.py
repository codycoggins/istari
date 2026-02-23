"""Tests for post-turn memory extraction."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from istari.agents.memory_extractor import extract_and_store

_LLM = "istari.agents.memory_extractor.completion"
_STORE = "istari.agents.memory_extractor.MemoryStore"


def _make_llm_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_factory():
    """Return a minimal session factory whose session is a MagicMock."""
    mock_session = AsyncMock()

    class Factory:
        def __call__(self):
            class CM:
                async def __aenter__(self):
                    return mock_session
                async def __aexit__(self, *a):
                    pass
            return CM()

    return Factory(), mock_session


class TestExtractAndStore:
    async def test_stores_extracted_facts(self):
        facts = ["User is an engineer at Acme Corp", "User prefers dark mode"]
        factory, mock_session = _make_factory()

        mock_store = AsyncMock()
        mock_store.list_explicit.return_value = []

        with patch(_LLM, new_callable=AsyncMock) as mock_llm, \
             patch(_STORE, return_value=mock_store):
            mock_llm.return_value = _make_llm_response(json.dumps(facts))
            await extract_and_store("I work at Acme", "Got it!", factory)

        stored = [c.args[0] for c in mock_store.store.call_args_list]
        assert "User is an engineer at Acme Corp" in stored
        assert "User prefers dark mode" in stored
        mock_session.commit.assert_called_once()

    async def test_skips_duplicate_facts(self):
        existing = MagicMock()
        existing.content = "User prefers dark mode"
        factory, _ = _make_factory()

        mock_store = AsyncMock()
        mock_store.list_explicit.return_value = [existing]

        with patch(_LLM, new_callable=AsyncMock) as mock_llm, \
             patch(_STORE, return_value=mock_store):
            mock_llm.return_value = _make_llm_response('["User prefers dark mode"]')
            await extract_and_store("I like dark mode", "Noted!", factory)

        mock_store.store.assert_not_called()

    async def test_empty_array_stores_nothing(self):
        factory, mock_session = _make_factory()
        mock_store = AsyncMock()
        mock_store.list_explicit.return_value = []

        with patch(_LLM, new_callable=AsyncMock) as mock_llm, \
             patch(_STORE, return_value=mock_store):
            mock_llm.return_value = _make_llm_response("[]")
            await extract_and_store("Mark my todo done", "Done!", factory)

        mock_store.store.assert_not_called()
        mock_session.commit.assert_not_called()

    async def test_llm_error_does_not_raise(self):
        factory, _ = _make_factory()

        with patch(_LLM, new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM unavailable")
            # Should not raise
            await extract_and_store("hello", "world", factory)

    async def test_bad_json_does_not_raise(self):
        factory, _ = _make_factory()

        with patch(_LLM, new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _make_llm_response("not valid json at all")
            await extract_and_store("hello", "world", factory)

    async def test_strips_markdown_fences(self):
        facts_json = '["User loves Python"]'
        wrapped = f"```json\n{facts_json}\n```"
        factory, _ = _make_factory()

        mock_store = AsyncMock()
        mock_store.list_explicit.return_value = []

        with patch(_LLM, new_callable=AsyncMock) as mock_llm, \
             patch(_STORE, return_value=mock_store):
            mock_llm.return_value = _make_llm_response(wrapped)
            await extract_and_store("I love Python", "Great!", factory)

        stored = [c.args[0] for c in mock_store.store.call_args_list]
        assert "User loves Python" in stored

    async def test_case_insensitive_dedup(self):
        existing = MagicMock()
        existing.content = "User prefers DARK MODE"
        factory, _ = _make_factory()

        mock_store = AsyncMock()
        mock_store.list_explicit.return_value = [existing]

        with patch(_LLM, new_callable=AsyncMock) as mock_llm, \
             patch(_STORE, return_value=mock_store):
            mock_llm.return_value = _make_llm_response('["User prefers dark mode"]')
            await extract_and_store("dark mode chat", "ok", factory)

        mock_store.store.assert_not_called()
