"""Tests for ProjectManager — CRUD against SQLite test DB."""

import datetime

import pytest

from istari.models.project import ProjectStatus
from istari.tools.project.manager import ProjectManager
from istari.tools.todo.manager import TodoManager


class TestProjectManagerCRUD:
    async def test_create_project(self, db_session):
        mgr = ProjectManager(db_session)
        project = await mgr.create("Launch website")
        assert project.id is not None
        assert project.name == "Launch website"
        assert project.status.value == "active"

    async def test_create_with_description_and_goal(self, db_session):
        mgr = ProjectManager(db_session)
        project = await mgr.create(
            "Q1 Roadmap",
            description="Plan for Q1",
            goal="Ship three features",
        )
        assert project.description == "Plan for Q1"
        assert project.goal == "Ship three features"

    async def test_get_project(self, db_session):
        mgr = ProjectManager(db_session)
        created = await mgr.create("Test project")
        fetched = await mgr.get(created.id)
        assert fetched is not None
        assert fetched.name == "Test project"

    async def test_get_nonexistent_returns_none(self, db_session):
        mgr = ProjectManager(db_session)
        assert await mgr.get(9999) is None

    async def test_list_active_returns_only_active(self, db_session):
        mgr = ProjectManager(db_session)
        await mgr.create("Active project")
        p2 = await mgr.create("Paused project")
        await mgr.set_status(p2.id, ProjectStatus.paused)

        active = await mgr.list_active()
        names = [p.name for p in active]
        assert "Active project" in names
        assert "Paused project" not in names

    async def test_list_all_returns_all(self, db_session):
        mgr = ProjectManager(db_session)
        await mgr.create("Active")
        p2 = await mgr.create("Complete")
        await mgr.set_status(p2.id, ProjectStatus.complete)

        all_projects = await mgr.list_all()
        assert len(all_projects) == 2

    async def test_get_by_name_ilike(self, db_session):
        mgr = ProjectManager(db_session)
        await mgr.create("Website Redesign")
        await mgr.create("Mobile App")

        results = await mgr.get_by_name("website")
        assert len(results) == 1
        assert results[0].name == "Website Redesign"

    async def test_get_by_name_no_match(self, db_session):
        mgr = ProjectManager(db_session)
        await mgr.create("Some project")
        results = await mgr.get_by_name("nonexistent")
        assert len(results) == 0

    async def test_set_next_action(self, db_session):
        proj_mgr = ProjectManager(db_session)
        todo_mgr = TodoManager(db_session)

        project = await proj_mgr.create("My project")
        todo = await todo_mgr.create("First task")

        updated = await proj_mgr.set_next_action(project.id, todo.id)
        assert updated.next_action_id == todo.id

    async def test_set_next_action_clear(self, db_session):
        proj_mgr = ProjectManager(db_session)
        todo_mgr = TodoManager(db_session)

        project = await proj_mgr.create("My project")
        todo = await todo_mgr.create("First task")
        await proj_mgr.set_next_action(project.id, todo.id)

        # Clear next action
        updated = await proj_mgr.set_next_action(project.id, None)
        assert updated.next_action_id is None

    async def test_set_next_action_invalid_project(self, db_session):
        mgr = ProjectManager(db_session)
        with pytest.raises(ValueError, match="not found"):
            await mgr.set_next_action(9999, 1)

    async def test_set_status(self, db_session):
        mgr = ProjectManager(db_session)
        project = await mgr.create("Status test")
        updated = await mgr.set_status(project.id, ProjectStatus.paused)
        assert updated.status == ProjectStatus.paused

    async def test_set_status_invalid_project(self, db_session):
        mgr = ProjectManager(db_session)
        with pytest.raises(ValueError, match="not found"):
            await mgr.set_status(9999, ProjectStatus.complete)

    async def test_get_with_todos(self, db_session):
        proj_mgr = ProjectManager(db_session)
        todo_mgr = TodoManager(db_session)

        project = await proj_mgr.create("Project with todos")
        todo = await todo_mgr.create("Task A")
        todo.project_id = project.id
        await db_session.flush()

        loaded = await proj_mgr.get_with_todos(project.id)
        assert loaded is not None
        assert any(t.id == todo.id for t in loaded.todos)


class TestProjectManagerStale:
    async def test_get_stale_returns_active_with_no_recent_todos(self, db_session):
        mgr = ProjectManager(db_session)
        project = await mgr.create("Stale project")
        # No todos associated — should be stale
        stale = await mgr.get_stale(days=7)
        assert any(p.id == project.id for p in stale)

    async def test_get_stale_excludes_projects_with_recent_todos(self, db_session):
        proj_mgr = ProjectManager(db_session)
        todo_mgr = TodoManager(db_session)

        project = await proj_mgr.create("Active project")
        todo = await todo_mgr.create("Recent task")
        todo.project_id = project.id
        # updated_at defaults to now(), so this todo is recent
        await db_session.flush()

        stale = await proj_mgr.get_stale(days=7)
        assert not any(p.id == project.id for p in stale)

    async def test_get_stale_excludes_paused_projects(self, db_session):
        mgr = ProjectManager(db_session)
        project = await mgr.create("Paused project")
        await mgr.set_status(project.id, ProjectStatus.paused)

        stale = await mgr.get_stale(days=7)
        assert not any(p.id == project.id for p in stale)

    async def test_get_stale_excludes_complete_projects(self, db_session):
        mgr = ProjectManager(db_session)
        project = await mgr.create("Done project")
        await mgr.set_status(project.id, ProjectStatus.complete)

        stale = await mgr.get_stale(days=7)
        assert not any(p.id == project.id for p in stale)

    async def test_get_stale_with_old_todo(self, db_session):
        proj_mgr = ProjectManager(db_session)
        todo_mgr = TodoManager(db_session)

        project = await proj_mgr.create("Project with old todo")
        todo = await todo_mgr.create("Old task")
        todo.project_id = project.id

        # Manually set updated_at to 30 days ago
        old_date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=30)
        todo.updated_at = old_date
        await db_session.flush()

        stale = await proj_mgr.get_stale(days=7)
        assert any(p.id == project.id for p in stale)
