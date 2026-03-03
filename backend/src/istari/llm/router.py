"""LLM routing — LiteLLM wrapper with model selection per task type."""

from typing import Any

import litellm

from istari.config.settings import settings
from istari.llm.config import get_model_config

# Suppress LiteLLM's verbose logging
litellm.suppress_debug_info = True

# Pre-register local Ollama models so LiteLLM's cost calculator doesn't fire a
# preflight GET to /api/show (which produces a noisy 404 because LiteLLM passes
# the full /api/generate URL as the base rather than just the host).
_OLLAMA_STUB: dict[str, Any] = {
    "litellm_provider": "ollama",
    "mode": "chat",
    "max_tokens": 8192,
    "max_input_tokens": 8192,
    "max_output_tokens": 8192,
    "input_cost_per_token": 0.0,
    "output_cost_per_token": 0.0,
}
litellm.model_cost.update(
    {
        "ollama/llama3.1:8b-instruct-q8_0": _OLLAMA_STUB,
        "ollama/mistral:7b-instruct-q8_0": _OLLAMA_STUB,
        "ollama/nomic-embed-text": {**_OLLAMA_STUB, "mode": "embedding"},
    }
)


async def completion(
    task_type: str,
    messages: list[dict[str, Any]],
    *,
    sensitive: bool = False,
    **kwargs: object,
) -> litellm.ModelResponse:
    """Route a completion request to the appropriate model based on task type.

    If sensitive=True, forces local model (ollama/llama3) regardless of task config.
    """
    config = get_model_config(task_type)
    model = config["model"]

    if sensitive:
        model = "ollama/llama3"

    call_kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": config.get("temperature", 0.7),
    }

    if model.startswith("ollama/"):
        call_kwargs["api_base"] = settings.ollama_base_url
        call_kwargs["num_ctx"] = 8192
    elif model.startswith("anthropic/"):
        call_kwargs["api_key"] = settings.anthropic_api_key
    elif model.startswith("gemini/"):
        call_kwargs["api_key"] = settings.google_api_key
    elif model.startswith("openai/"):
        call_kwargs["api_key"] = settings.openai_api_key

    call_kwargs.update(kwargs)
    return await litellm.acompletion(**call_kwargs)


async def embedding(text: str) -> list[float]:
    """Generate an embedding vector using the configured embedding model."""
    config = get_model_config("embedding")
    model = config["model"]

    emb_kwargs: dict[str, Any] = {
        "model": model,
        "input": [text],
    }

    if model.startswith("ollama/"):
        emb_kwargs["api_base"] = settings.ollama_base_url

    response = await litellm.aembedding(**emb_kwargs)
    return response.data[0]["embedding"]  # type: ignore[no-any-return]
