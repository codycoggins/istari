"""Base types and shared utilities for agent tools."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

# Map common user phrasings to valid TodoStatus values
STATUS_SYNONYMS: dict[str, str] = {
    "done": "complete",
    "finished": "complete",
    "finish": "complete",
    "completed": "complete",
    "close": "complete",
    "closed": "complete",
    "started": "in_progress",
    "start": "in_progress",
    "begin": "in_progress",
    "working on": "in_progress",
    "in progress": "in_progress",
    "stuck": "blocked",
    "waiting": "blocked",
    "on hold": "blocked",
    "postpone": "deferred",
    "defer": "deferred",
    "snooze": "deferred",
    "later": "deferred",
    "skip": "deferred",
}


def normalize_status(raw: str) -> str:
    """Normalize a user-supplied status string to a valid TodoStatus value."""
    key = raw.strip().lower()
    return STATUS_SYNONYMS.get(key, key)


@dataclass
class AgentContext:
    """Mutable side-effect flags populated by tools during an agent run."""

    todo_created: bool = False
    todo_updated: bool = False
    memory_created: bool = False


@dataclass
class AgentTool:
    """A single callable tool exposed to the LLM."""

    name: str
    description: str
    parameters: dict  # JSON Schema "parameters" object (type, properties, required)
    fn: Callable[..., Awaitable[str]]
    _required: list[str] = field(default_factory=list, repr=False)

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
