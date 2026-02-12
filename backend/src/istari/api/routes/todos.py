"""TODO CRUD endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("/")
async def list_todos() -> dict:
    return {"todos": []}
