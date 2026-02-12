"""Memory view endpoint — shows what Istari has learned."""

from fastapi import APIRouter

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/")
async def get_memory_summary() -> dict:
    return {"memories": []}
