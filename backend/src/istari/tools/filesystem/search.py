"""Filesystem search tool — search local files by name, content, recency. Read-only."""

from pathlib import Path

_MAX_FILES = 500
_PREVIEW_LEN = 120


def search_text_in_files(
    query: str,
    directory: str = "~",
    extensions: str = "",
    max_files: int = _MAX_FILES,
    max_results: int = 10,
) -> list[tuple[str, str]]:
    """Search files under *directory* whose text content contains *query*.

    Returns a list of (file_path_str, preview_line) tuples, capped at
    *max_results*.  Skips binary files silently.  Scans at most *max_files*
    files to avoid runaway traversal.

    Args:
        query: Case-insensitive substring to search for.
        directory: Root dir to search (supports ``~`` expansion). Defaults to
            the user's home directory.
        extensions: Comma-separated file extensions without dots, e.g.
            ``"md,txt,py"``.  Empty string means all files.
        max_files: Hard scan limit to prevent runaway searches.
        max_results: Maximum number of matching files to return.
    """
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        return []

    ext_set: set[str] = set()
    if extensions:
        ext_set = {e.strip().lstrip(".").lower() for e in extensions.split(",") if e.strip()}

    q_lower = query.lower()
    matches: list[tuple[str, str]] = []
    scanned = 0

    for path in root.rglob("*"):
        if scanned >= max_files:
            break
        if not path.is_file():
            continue
        if ext_set and path.suffix.lstrip(".").lower() not in ext_set:
            continue

        scanned += 1
        try:
            text = path.read_bytes()
            decoded = text.decode("utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue

        if q_lower not in decoded.lower():
            continue

        # Find the first matching line as a preview
        preview = ""
        for line in decoded.splitlines():
            if q_lower in line.lower():
                preview = line.strip()[:_PREVIEW_LEN]
                break

        matches.append((str(path), preview))
        if len(matches) >= max_results:
            break

    return matches
