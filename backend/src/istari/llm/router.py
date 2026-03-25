"""LLM routing — multi-provider wrapper with model selection per task type."""

from typing import Any, cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from istari.config.settings import settings
from istari.llm.config import get_model_config


def _make_client(model: str) -> tuple[AsyncOpenAI, str]:
    """Return (client, bare_model_name) for any supported model prefix."""
    if model.startswith("ollama/"):
        return (
            AsyncOpenAI(base_url=f"{settings.ollama_base_url}/v1", api_key="ollama"),
            model.removeprefix("ollama/"),
        )
    if model.startswith("anthropic/"):
        return (
            AsyncOpenAI(
                base_url="https://api.anthropic.com/v1",
                api_key=settings.anthropic_api_key or "",
                default_headers={"anthropic-version": "2023-06-01"},
            ),
            model.removeprefix("anthropic/"),
        )
    if model.startswith("gemini/"):
        return (
            AsyncOpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=settings.google_api_key or "",
            ),
            model.removeprefix("gemini/"),
        )
    # openai/ prefix or bare model name
    return (
        AsyncOpenAI(api_key=settings.openai_api_key or ""),
        model.removeprefix("openai/"),
    )


async def completion(
    task_type: str,
    messages: list[dict[str, Any]],
    *,
    sensitive: bool = False,
    **kwargs: object,
) -> ChatCompletion:
    """Route a completion request to the appropriate model based on task type.

    If sensitive=True, forces local model (ollama/llama3) regardless of task config.
    """
    config = get_model_config(task_type)
    model = config["model"]

    if sensitive:
        model = "ollama/llama3"

    client, bare_model = _make_client(model)

    call_kwargs: dict[str, Any] = {
        "model": bare_model,
        "messages": messages,
        "temperature": config.get("temperature", 0.7),
    }

    if model.startswith("ollama/"):
        call_kwargs["extra_body"] = {"num_ctx": 8192}

    call_kwargs.update(kwargs)
    return cast(ChatCompletion, await client.chat.completions.create(**call_kwargs))


async def embedding(text: str) -> list[float]:
    """Generate an embedding vector using the configured embedding model."""
    config = get_model_config("embedding")
    model = config["model"]

    client, bare_model = _make_client(model)
    response = await client.embeddings.create(model=bare_model, input=[text])
    return response.data[0].embedding
