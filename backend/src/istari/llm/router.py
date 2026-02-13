"""LLM routing — LiteLLM wrapper with model selection per task type."""

import litellm

from istari.config.settings import settings
from istari.llm.config import get_model_config

# Suppress LiteLLM's verbose logging
litellm.suppress_debug_info = True


async def completion(
    task_type: str,
    messages: list[dict],  # type: ignore[type-arg]
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

    call_kwargs: dict[str, object] = {
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

    call_kwargs.update(kwargs)
    return await litellm.acompletion(**call_kwargs)  # type: ignore[arg-type]


async def embedding(text: str) -> list[float]:
    """Generate an embedding vector using the configured embedding model."""
    config = get_model_config("embedding")
    model = config["model"]

    emb_kwargs: dict[str, object] = {
        "model": model,
        "input": [text],
    }

    if model.startswith("ollama/"):
        emb_kwargs["api_base"] = settings.ollama_base_url

    response = await litellm.aembedding(**emb_kwargs)  # type: ignore[arg-type]
    return response.data[0]["embedding"]  # type: ignore[index,return-value]
