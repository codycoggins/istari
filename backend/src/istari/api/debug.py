"""In-process error ring buffer — last N WARNING+ log records, queryable via API."""

import datetime
import logging
from collections import deque
from collections.abc import Iterator
from typing import Any


class RingBufferHandler(logging.Handler):
    """Logging handler that keeps the last `maxlen` records at WARNING or above."""

    def __init__(self, maxlen: int = 50) -> None:
        super().__init__(level=logging.WARNING)
        self._buffer: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        ts = datetime.datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        self._buffer.append(
            {
                "timestamp": ts,
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
        )

    def records(self) -> Iterator[dict[str, Any]]:
        yield from self._buffer


# Module-level singleton — attached to root logger in lifespan
ring_buffer = RingBufferHandler(maxlen=50)


def get_recent_errors() -> list[dict[str, Any]]:
    """Return all buffered WARNING+ records (oldest first)."""
    return list(ring_buffer.records())
