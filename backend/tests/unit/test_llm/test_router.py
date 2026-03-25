"""Tests for LLM router — model selection and sensitive routing."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_client(content: str = "Hello!") -> MagicMock:
    """Build a fake AsyncOpenAI client whose create methods return canned responses."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None

    choice = MagicMock()
    choice.message = msg

    chat_response = MagicMock()
    chat_response.choices = [choice]

    emb_item = MagicMock()
    emb_item.embedding = [0.1] * 768

    emb_response = MagicMock()
    emb_response.data = [emb_item]

    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=chat_response)
    client.embeddings.create = AsyncMock(return_value=emb_response)
    return client


@pytest.fixture
def mock_client():
    client = _mock_client()
    with patch("istari.llm.router.AsyncOpenAI", return_value=client):
        yield client


class TestCompletion:
    async def test_routes_to_configured_model(self, mock_client):
        from istari.llm.config import get_model_config
        from istari.llm.router import completion

        messages = [{"role": "user", "content": "Hello"}]
        await completion("chat_response", messages)

        expected_model = get_model_config("chat_response")["model"]
        # bare model name — prefix stripped
        expected_bare = expected_model.split("/", 1)[-1]
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == expected_bare

    async def test_sensitive_forces_local_model(self):
        """sensitive=True must create an ollama client (base_url contains ollama port)."""
        from istari.llm.router import completion

        client = _mock_client()
        messages = [{"role": "user", "content": "Hello"}]
        with patch("istari.llm.router.AsyncOpenAI", return_value=client) as mock_cls:
            await completion("chat_response", messages, sensitive=True)
            init_kwargs = mock_cls.call_args.kwargs
            assert "base_url" in init_kwargs
            assert "11434" in init_kwargs["base_url"]

    async def test_ollama_gets_num_ctx_in_extra_body(self, mock_client):
        from istari.llm.router import completion

        messages = [{"role": "user", "content": "Summarize this"}]
        await completion("summarization", messages)

        call_kwargs = mock_client.chat.completions.create.call_args
        # summarization task is ollama in dev config
        model_config_model = call_kwargs.kwargs.get("model", "")
        extra_body = call_kwargs.kwargs.get("extra_body", {})
        # If the model came via ollama client, extra_body should have num_ctx
        # (or the test is running against a non-ollama summarization model — skip)
        from istari.llm.config import get_model_config
        if get_model_config("summarization")["model"].startswith("ollama/"):
            assert extra_body.get("num_ctx") == 8192
        else:
            assert model_config_model  # just verify a call was made

    async def test_anthropic_client_gets_correct_base_url(self):
        """anthropic/ models must use the Anthropic API base URL."""
        from istari.llm.router import _make_client

        with patch("istari.llm.router.AsyncOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            _make_client("anthropic/claude-3-5-sonnet-20241022")
            init_kwargs = mock_cls.call_args.kwargs
            assert "anthropic.com" in init_kwargs["base_url"]

    async def test_default_model_for_unknown_task(self, mock_client):
        from istari.llm.config import get_model_config
        from istari.llm.router import completion

        messages = [{"role": "user", "content": "Hello"}]
        await completion("unknown_task_type", messages)

        expected_bare = get_model_config("unknown_task_type")["model"].split("/", 1)[-1]
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == expected_bare

    async def test_temperature_passed(self, mock_client):
        from istari.llm.router import completion

        messages = [{"role": "user", "content": "Hello"}]
        await completion("classification", messages)

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["temperature"] == 0.0


class TestEmbedding:
    async def test_returns_vector(self, mock_client):
        from istari.llm.router import embedding

        result = await embedding("test text")
        assert len(result) == 768

    async def test_uses_configured_model(self, mock_client):
        from istari.llm.router import embedding

        await embedding("test text")
        call_kwargs = mock_client.embeddings.create.call_args
        # bare model name (prefix stripped)
        assert call_kwargs.kwargs["model"] == "nomic-embed-text"
