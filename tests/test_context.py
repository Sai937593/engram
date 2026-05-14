"""Tests for context generation (startup and task context)."""
from engram.context import get_startup_context, get_task_context
from engram.models.task import Task
from engram.models.memory import Memory
from engram.models.session import Session


def test_startup_context_contains_project_name(project):
    ctx = get_startup_context(project.id)
    assert "Test Project" in ctx


def test_startup_context_shows_last_checkpoint(project):
    s = Session.create(project_id=project.id, goal="Do work")
    s.close(summary="Finished the thing", next_steps="Do more things")
    ctx = get_startup_context(project.id)
    assert "Finished the thing" in ctx
    assert "Do more things" in ctx


def test_startup_context_shows_always_include_memories(project):
    Memory.create(
        project_id=project.id,
        type="constraint",
        title="Never write to prod",
        content="Do not touch production DB.",
        always_include=True,
    )
    ctx = get_startup_context(project.id)
    assert "Never write to prod" in ctx


def test_startup_context_shows_active_tasks(project):
    Task.create(project_id=project.id, title="My active task", status="todo")
    ctx = get_startup_context(project.id)
    assert "My active task" in ctx


def test_startup_context_no_crash_when_empty(project):
    """Startup context should work gracefully even with no tasks or sessions."""
    ctx = get_startup_context(project.id)
    assert "Test Project" in ctx


def test_task_context_shows_title(task):
    ctx = get_task_context(task.id)
    assert task.title in ctx


def test_task_context_shows_acceptance(project):
    t = Task.create(
        project_id=project.id,
        title="Feature with acceptance",
        acceptance="Must pass all unit tests.",
    )
    ctx = get_task_context(t.id)
    assert "Must pass all unit tests." in ctx


def test_task_context_not_found():
    ctx = get_task_context("nonexistent-id")
    assert "not found" in ctx.lower()
