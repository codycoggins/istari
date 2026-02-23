"""Filesystem agent tools — read and search local files."""

import asyncio
import logging
from pathlib import Path

from .base import AgentTool

logger = logging.getLogger(__name__)

_MAX_CHARS = 8_000


def make_filesystem_tools() -> list[AgentTool]:
    """Return filesystem tools. No session or context needed — read-only."""

    async def read_file(path: str) -> str:
        resolved = Path(path).expanduser()
        if not resolved.is_absolute():
            resolved = Path.home() / resolved

        try:
            raw = await asyncio.to_thread(resolved.read_bytes)
        except FileNotFoundError:
            return f"File not found: {resolved}"
        except PermissionError:
            return f"Permission denied: {resolved}"
        except OSError as exc:
            return f"Could not read file: {exc}"

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return f"Cannot read {resolved.name}: file appears to be binary."

        if len(text) <= _MAX_CHARS:
            return text

        truncated = text[:_MAX_CHARS]
        remaining = len(text) - _MAX_CHARS
        return f"{truncated}\n\n[...truncated — {remaining} more characters not shown]"

    async def search_files(
        query: str,
        directory: str = "~",
        extensions: str = "",
    ) -> str:
        from istari.tools.filesystem.search import search_text_in_files

        results = await asyncio.to_thread(
            search_text_in_files,
            query,
            directory,
            extensions,
        )

        if not results:
            ext_note = f" with extensions [{extensions}]" if extensions else ""
            return (
                f'No files containing "{query}" found in {directory}{ext_note}.'
            )

        lines = [f"- {p}\n  Preview: {preview}" for p, preview in results]
        return (
            f'Found {len(results)} file(s) containing "{query}":\n'
            + "\n".join(lines)
        )

    return [
        AgentTool(
            name="read_file",
            description=(
                "Read the contents of a local file. Supports plain text, "
                "markdown, JSON, CSV, Python, etc. Use ~ for the home directory."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "File path to read. Absolute or relative to home dir. "
                            "Example: ~/Documents/notes.md"
                        ),
                    }
                },
                "required": ["path"],
            },
            fn=read_file,
        ),
        AgentTool(
            name="search_files",
            description=(
                "Search local files for text content. Returns matching file paths "
                "with a preview of the matching line."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to search for (case-insensitive).",
                    },
                    "directory": {
                        "type": "string",
                        "description": (
                            "Directory to search in. Defaults to ~ (home dir). "
                            "Example: ~/Documents"
                        ),
                    },
                    "extensions": {
                        "type": "string",
                        "description": (
                            "Comma-separated file extensions to include, e.g. "
                            "'md,txt,py'. Leave empty to search all files."
                        ),
                    },
                },
                "required": ["query"],
            },
            fn=search_files,
        ),
    ]
