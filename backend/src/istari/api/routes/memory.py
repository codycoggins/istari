"""Memory view endpoint — shows what Istari has learned."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from istari.api.deps import get_db
from istari.api.schemas import MemoryCreate, MemoryListResponse, MemoryResponse
from istari.tools.memory.store import MemoryStore

router = APIRouter(prefix="/memory", tags=["memory"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=MemoryListResponse)
async def list_memories(db: DB) -> MemoryListResponse:
    store = MemoryStore(db)
    memories = await store.list_explicit()
    return MemoryListResponse(
        memories=[MemoryResponse.model_validate(m) for m in memories],
    )


@router.post("/", response_model=MemoryResponse, status_code=201)
async def create_memory(body: MemoryCreate, db: DB) -> MemoryResponse:
    store = MemoryStore(db)
    memory = await store.store(content=body.content)
    await db.commit()
    await db.refresh(memory)
    return MemoryResponse.model_validate(memory)
