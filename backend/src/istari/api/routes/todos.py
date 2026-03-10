"""TODO CRUD endpoints."""

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from istari.api.deps import get_db
from istari.api.schemas import (
    PrioritizedTodosResponse,
    TodoContextResponse,
    TodoCreate,
    TodoListResponse,
    TodoResponse,
    TodoUpdate,
)
from istari.config.settings import settings
from istari.tools.todo.manager import TodoManager

router = APIRouter(prefix="/todos", tags=["todos"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=TodoListResponse)
async def list_todos(db: DB) -> TodoListResponse:
    mgr = TodoManager(db)
    todos = await mgr.list_visible()
    return TodoListResponse(todos=[TodoResponse.model_validate(t) for t in todos])


@router.post("/", response_model=TodoResponse, status_code=201)
async def create_todo(body: TodoCreate, db: DB) -> TodoResponse:
    mgr = TodoManager(db)
    todo = await mgr.create(title=body.title)
    await db.commit()
    await db.refresh(todo)
    return TodoResponse.model_validate(todo)


@router.get("/today", response_model=TodoListResponse)
async def list_today_todos(db: DB) -> TodoListResponse:
    mgr = TodoManager(db)
    todos = await mgr.list_today()
    return TodoListResponse(todos=[TodoResponse.model_validate(t) for t in todos])


@router.post("/{todo_id}/today", response_model=TodoResponse)
async def toggle_today(todo_id: int, db: DB) -> TodoResponse:
    mgr = TodoManager(db)
    todo = await mgr.get(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    flag = todo.today_date != datetime.date.today()
    todo = await mgr.set_today(todo_id, flag)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    await db.commit()
    await db.refresh(todo)
    return TodoResponse.model_validate(todo)


@router.get("/prioritized", response_model=PrioritizedTodosResponse)
async def get_prioritized(db: DB) -> PrioritizedTodosResponse:
    mgr = TodoManager(db)
    todos = await mgr.get_prioritized(limit=settings.priorities_max)
    return PrioritizedTodosResponse(
        todos=[TodoResponse.model_validate(t) for t in todos],
    )


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: int, db: DB) -> TodoResponse:
    mgr = TodoManager(db)
    todo = await mgr.get(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return TodoResponse.model_validate(todo)


@router.patch("/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: int, body: TodoUpdate, db: DB) -> TodoResponse:
    mgr = TodoManager(db)
    updates = body.model_dump(exclude_unset=True)
    todo = await mgr.update(todo_id, **updates)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    await db.commit()
    await db.refresh(todo)
    return TodoResponse.model_validate(todo)


@router.post("/{todo_id}/context", response_model=TodoContextResponse)
async def get_todo_context(todo_id: int, db: DB) -> TodoContextResponse:
    from istari.agents.todo_context import get_todo_context as _gather_context

    mgr = TodoManager(db)
    todo = await mgr.get(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    context_text = await _gather_context(todo.title, db)
    return TodoContextResponse(context=context_text)


@router.post("/{todo_id}/complete", response_model=TodoResponse)
async def complete_todo(todo_id: int, db: DB) -> TodoResponse:
    mgr = TodoManager(db)
    todo = await mgr.complete(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    await db.commit()
    await db.refresh(todo)
    return TodoResponse.model_validate(todo)
