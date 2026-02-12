"""LLM routing — LiteLLM wrapper with model selection per task type."""

from istari.llm.config import get_model_config


async def completion(task_type: str, messages: list[dict], **kwargs) -> dict:  # type: ignore[type-arg]
    """Route a completion request to the appropriate model based on task type.

    The content classifier must be invoked BEFORE calling this function.
    """
    _config = get_model_config(task_type)
    # LiteLLM integration will be wired here
    raise NotImplementedError(f"LLM routing not yet implemented for task: {task_type}")
