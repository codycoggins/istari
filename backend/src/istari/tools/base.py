"""Tool protocol/interface and read-only enforcement."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ReadOnlyTool(Protocol):
    """All external-facing tools must implement this protocol.

    External tools are structurally read-only — no write methods exist.
    Internal tools (todo_manager, memory_store) may write to the database.
    """

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    async def execute(self, **kwargs: object) -> dict:  # type: ignore[type-arg]
        """Execute the tool with the given parameters."""
        ...
