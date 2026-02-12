"""Placeholder test to verify test scaffolding works."""

from istari.models.todo import TodoStatus


def test_todo_status_values():
    assert TodoStatus.ACTIVE == "active"
    assert TodoStatus.COMPLETED == "completed"
    assert TodoStatus.DEFERRED == "deferred"
