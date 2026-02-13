"""Tests for LLM router — model selection and sensitive routing."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_acompletion():
    with patch("istari.llm.router.litellm.acompletion", new_callable=AsyncMock) as mock:
        mock.return_value = {"choices": [{"message": {"content": "Hello!"}}]}
        yield mock


@pytest.fixture
def mock_aembedding():
    with patch("istari.llm.router.litellm.aembedding", new_callable=AsyncMock) as mock:
        mock.return_value = type("R", (), {"data": [{"embedding": [0.1] * 768}]})()
        yield mock


class TestCompletion:
    async def test_routes_to_configured_model(self, mock_acompletion):
        from istari.llm.router import completion

        messages = [{"role": "user", "content": "Hello"}]
        await completion("chat_response", messages)

        call_kwargs = mock_acompletion.call_args
        assert call_kwargs.kwargs["model"] == "anthropic/claude-sonnet-4-20250514"

    async def test_sensitive_forces_local_model(self, mock_acompletion):
        from istari.llm.router import completion

        messages = [{"role": "user", "content": "Hello"}]
        await completion("chat_response", messages, sensitive=True)

        call_kwargs = mock_acompletion.call_args
        assert call_kwargs.kwargs["model"] == "ollama/llama3"

    async def test_ollama_gets_api_base_and_num_ctx(self, mock_acompletion):
        from istari.llm.router import completion

        messages = [{"role": "user", "content": "Summarize this"}]
        await completion("summarization", messages)

        call_kwargs = mock_acompletion.call_args
        assert call_kwargs.kwargs["model"] == "ollama/llama3"
        assert "api_base" in call_kwargs.kwargs
        assert call_kwargs.kwargs["num_ctx"] == 8192

    async def test_anthropic_gets_api_key(self, mock_acompletion):
        from istari.llm.router import completion

        messages = [{"role": "user", "content": "Hello"}]
        await completion("chat_response", messages)

        call_kwargs = mock_acompletion.call_args
        assert "api_key" in call_kwargs.kwargs

    async def test_default_model_for_unknown_task(self, mock_acompletion):
        from istari.llm.router import completion

        messages = [{"role": "user", "content": "Hello"}]
        await completion("unknown_task_type", messages)

        call_kwargs = mock_acompletion.call_args
        assert call_kwargs.kwargs["model"] == "ollama/llama3"

    async def test_temperature_passed(self, mock_acompletion):
        from istari.llm.router import completion

        messages = [{"role": "user", "content": "Hello"}]
        await completion("classification", messages)

        call_kwargs = mock_acompletion.call_args
        assert call_kwargs.kwargs["temperature"] == 0.0


class TestEmbedding:
    async def test_returns_vector(self, mock_aembedding):
        from istari.llm.router import embedding

        result = await embedding("test text")
        assert len(result) == 768

    async def test_uses_configured_model(self, mock_aembedding):
        from istari.llm.router import embedding

        await embedding("test text")
        call_kwargs = mock_aembedding.call_args
        assert call_kwargs.kwargs["model"] == "ollama/nomic-embed-text"
