"""Load LLM routing configuration from YAML."""

from istari.config.settings import settings


def get_model_config(task_type: str) -> dict:  # type: ignore[type-arg]
    """Get model configuration for a given task type."""
    routing = settings.llm_routing
    tasks = routing.get("tasks", {})
    if task_type in tasks:
        return tasks[task_type]
    return routing.get("defaults", {"model": "ollama/llama3", "temperature": 0.7})
