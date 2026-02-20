"""Tests for LLM config — model selection per task type."""

from istari.llm.config import get_model_config


class TestGetModelConfig:
    def test_chat_response_has_model(self):
        config = get_model_config("chat_response")
        assert config["model"]  # configured model exists

    def test_summarization_uses_ollama(self):
        config = get_model_config("summarization")
        assert config["model"].startswith("ollama/")

    def test_classification_zero_temperature(self):
        config = get_model_config("classification")
        assert config["temperature"] == 0.0

    def test_embedding_model(self):
        config = get_model_config("embedding")
        assert "nomic" in config["model"] or "embed" in config["model"]

    def test_unknown_task_returns_default(self):
        config = get_model_config("nonexistent_task")
        assert config["model"]  # falls back to a configured default

    def test_default_has_temperature(self):
        config = get_model_config("nonexistent_task")
        assert "temperature" in config
