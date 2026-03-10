"""Debug endpoints — in-process error ring buffer."""

from typing import Any

from fastapi import APIRouter

from istari.api.debug import get_recent_errors

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/recent-errors")
async def recent_errors() -> dict[str, Any]:
    """Return the last 50 WARNING+ log records captured in-process."""
    errors = get_recent_errors()
    return {"errors": errors, "count": len(errors)}
