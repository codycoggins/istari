"""Tests for project agent tools."""

from istari.agents.tools.base import AgentContext
from istari.agents.tools.projects import make_project_tools
from istari.tools.project.manager import ProjectManager
from istari.tools.todo.manager import TodoManager


class TestCreateProjectTool:
    async def test_create_project_returns_success(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_project_tools(db_session, ctx)}
        result = await tools["create_project"].fn(name="Website Redesign")

        assert "Website Redesign" in result
        assert "Created project" in result

        mgr = ProjectManager(db_session)
        projects = await mgr.list_active()
        assert any(p.name == "Website Redesign" for p in projects)

    async def test_create_project_with_goal(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_project_tools(db_session, ctx)}
        result = await tools["create_project"].fn(
            name="Q2 Launch",
            goal="Ship product by June 30",
        )

        assert "Q2 Launch" in result
        assert "Ship product by June 30" in result

    async def test_create_project_persists(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_project_tools(db_session, ctx)}
        await tools["create_project"].fn(name="Persisted project")

        mgr = ProjectManager(db_session)
        projects = await mgr.list_active()
        assert len(projects) == 1


class TestListProjectsTool:
    async def test_list_empty_returns_message(self, db_session):
        ctx = AgentContext()
        tools = {t.name: t for t in make_project_tools(db_session, ctx)}
        result = await tools["list_projects"].fn()

        assert "No" in result

    async def test_list_shows_project_name(self, db_session):
        mgr = ProjectManager(db_session)
        await mgr.create("My Big Project")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_project_tools(db_session, ctx)}
        result = await tools["list_projects"].fn()

        assert "My Big Project" in result

    async def test_list_shows_next_action(self, db_session):
        proj_mgr = ProjectManager(db_session)
        todo_mgr = TodoManager(db_session)

        project = await proj_mgr.create("Project with next action")
        todo = await todo_mgr.create("The next task")
        await proj_mgr.set_next_action(project.id, todo.id)
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_project_tools(db_session, ctx)}
        result = await tools["list_projects"].fn()

        assert "The next task" in result

    async def test_list_all_includes_complete(self, db_session):
        from istari.models.project import ProjectStatus

        mgr = ProjectManager(db_session)
        p = await mgr.create("Done project")
        await mgr.set_status(p.id, ProjectStatus.complete)
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_project_tools(db_session, ctx)}
        result = await tools["list_projects"].fn(status="all")

        assert "Done project" in result


class TestAddTodoToProjectTool:
    async def test_add_by_id(self, db_session):
        proj_mgr = ProjectManager(db_session)
        todo_mgr = TodoManager(db_session)

        project = await proj_mgr.create("My project")
        todo = await todo_mgr.create("Task to assign")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_project_tools(db_session, ctx)}
        result = await tools["add_todo_to_project"].fn(
            todo_query=str(todo.id),
            project_query=str(project.id),
        )

        assert "My project" in result
        assert "Task to assign" in result
        assert ctx.todo_updated is True

        refreshed = await todo_mgr.get(todo.id)
        assert refreshed is not None
        assert refreshed.project_id == project.id

    async def test_add_by_name_match(self, db_session):
        proj_mgr = ProjectManager(db_session)
        todo_mgr = TodoManager(db_session)

        await proj_mgr.create("Website Project")
        await todo_mgr.create("Design homepage mockup")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_project_tools(db_session, ctx)}
        result = await tools["add_todo_to_project"].fn(
            todo_query="homepage",
            project_query="Website",
        )

        assert "Website Project" in result
        assert ctx.todo_updated is True

    async def test_add_todo_not_found(self, db_session):
        proj_mgr = ProjectManager(db_session)
        project = await proj_mgr.create("My project")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_project_tools(db_session, ctx)}
        result = await tools["add_todo_to_project"].fn(
            todo_query="nonexistent task",
            project_query=str(project.id),
        )

        assert "No TODOs found" in result

    async def test_add_project_not_found(self, db_session):
        todo_mgr = TodoManager(db_session)
        todo = await todo_mgr.create("Some task")
        await db_session.flush()

        ctx = AgentContext()
        tools = {t.name: t for t in make_project_tools(db_session, ctx)}
        result = await tools["add_todo_to_project"].fn(
            todo_query=str(todo.id),
            project_query="nonexistent project",
        )

        assert "No projects found" in result
