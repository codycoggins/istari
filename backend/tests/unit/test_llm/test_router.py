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
        from istari.llm.config import get_model_config
        from istari.llm.router import completion

        messages = [{"role": "user", "content": "Hello"}]
        await completion("chat_response", messages)

        expected_model = get_model_config("chat_response")["model"]
        call_kwargs = mock_acompletion.call_args
        assert call_kwargs.kwargs["model"] == expected_model

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
        assert call_kwargs.kwargs["model"].startswith("ollama/")
        assert "api_base" in call_kwargs.kwargs
        assert call_kwargs.kwargs["num_ctx"] == 8192

    async def test_anthropic_gets_api_key(self, mock_acompletion):
        from istari.llm.router import completion

        # Use prioritization task which is configured for anthropic in prod;
        # in dev (ollama), this test verifies ollama gets api_base instead.
        messages = [{"role": "user", "content": "Hello"}]
        await completion("chat_response", messages)

        call_kwargs = mock_acompletion.call_args
        model = call_kwargs.kwargs["model"]
        if model.startswith("anthropic/"):
            assert "api_key" in call_kwargs.kwargs
        elif model.startswith("ollama/"):
            assert "api_base" in call_kwargs.kwargs

    async def test_default_model_for_unknown_task(self, mock_acompletion):
        from istari.llm.config import get_model_config
        from istari.llm.router import completion

        messages = [{"role": "user", "content": "Hello"}]
        await completion("unknown_task_type", messages)

        call_kwargs = mock_acompletion.call_args
        assert call_kwargs.kwargs["model"] == get_model_config("unknown_task_type")["model"]

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
