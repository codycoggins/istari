"""Project CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from istari.api.deps import get_db
from istari.api.schemas import (
    NextActionUpdate,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithTodos,
    TodoResponse,
)
from istari.models.project import ProjectStatus
from istari.tools.project.manager import ProjectManager

router = APIRouter(prefix="/projects", tags=["projects"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=ProjectListResponse)
async def list_projects(db: DB, status: str = "active") -> ProjectListResponse:
    mgr = ProjectManager(db)
    if status == "all":
        projects = await mgr.list_all()
    else:
        projects = await mgr.list_active()
    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects]
    )


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate, db: DB) -> ProjectResponse:
    mgr = ProjectManager(db)
    project = await mgr.create(
        name=body.name,
        description=body.description,
        goal=body.goal,
    )
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectWithTodos)
async def get_project(project_id: int, db: DB) -> ProjectWithTodos:
    mgr = ProjectManager(db)
    project = await mgr.get_with_todos(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectWithTodos(
        **ProjectResponse.model_validate(project).model_dump(),
        todos=[TodoResponse.model_validate(t) for t in project.todos],
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: int, body: ProjectUpdate, db: DB) -> ProjectResponse:
    mgr = ProjectManager(db)
    updates = body.model_dump(exclude_unset=True)
    # Coerce status string to enum if present
    if "status" in updates and updates["status"] is not None:
        try:
            updates["status"] = ProjectStatus(updates["status"])
        except ValueError:
            valid = ", ".join(s.value for s in ProjectStatus)
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status. Valid values: {valid}",
            ) from None
    project = await mgr.update(project_id, **updates)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/next-action", response_model=ProjectResponse)
async def set_next_action(
    project_id: int, body: NextActionUpdate, db: DB
) -> ProjectResponse:
    mgr = ProjectManager(db)
    project = await mgr.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        project = await mgr.set_next_action(project_id, body.todo_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", response_model=ProjectResponse)
async def delete_project(project_id: int, db: DB) -> ProjectResponse:
    """Soft-delete: set status to complete."""
    mgr = ProjectManager(db)
    project = await mgr.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    project = await mgr.set_status(project_id, ProjectStatus.complete)
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)
