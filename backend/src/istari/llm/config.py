"""Load LLM routing configuration from YAML."""

from typing import Any

from istari.config.settings import settings


def get_model_config(task_type: str) -> dict[str, Any]:
    """Get model configuration for a given task type."""
    routing = settings.llm_routing
    tasks = routing.get("tasks", {})
    if task_type in tasks:
        return tasks[task_type]  # type: ignore[no-any-return]
    return routing.get("defaults", {"model": "ollama/llama3", "temperature": 0.7})  # type: ignore[no-any-return]
