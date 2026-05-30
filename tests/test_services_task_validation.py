import pytest

from engram.db import get_db_connection
from engram.services.errors import ValidationError
from engram.services.task.validation import _check_dependency_cycle


def test_no_dependency(tmp_db):
    """Test that passing depends_on_id=None returns early."""
    # Should return early, no DB query needed
    _check_dependency_cycle("task-1", None, "project-1")


def test_no_cycle(tmp_db):
    """Test that a valid dependency chain (A -> B -> C) does not raise an error."""
    conn = get_db_connection()
    # A -> B -> C
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, status, depends_on) VALUES "
        "('task-b', 'proj-1', 'Task B', 'todo', 'task-c'), "
        "('task-c', 'proj-1', 'Task C', 'todo', NULL)"
    )
    conn.commit()
    conn.close()

    # Checking if 'task-a' can depend on 'task-b'
    _check_dependency_cycle("task-a", "task-b", "proj-1")


def test_direct_cycle(tmp_db):
    """Test that a direct cycle (A -> B, B -> A) raises ValidationError."""
    conn = get_db_connection()
    # A -> B is the new edge we're checking, B -> A already exists
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, status, depends_on) VALUES "
        "('task-b', 'proj-1', 'Task B', 'todo', 'task-a')"
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValidationError) as exc_info:
        _check_dependency_cycle("task-a", "task-b", "proj-1")
    assert exc_info.value.code == "DEPENDENCY_CYCLE"


def test_indirect_cycle(tmp_db):
    """Test that an indirect cycle (A -> B -> C -> A) raises ValidationError."""
    conn = get_db_connection()
    # A -> B is what we check.
    # We already have B -> C and C -> A
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, status, depends_on) VALUES "
        "('task-b', 'proj-1', 'Task B', 'todo', 'task-c'), "
        "('task-c', 'proj-1', 'Task C', 'todo', 'task-a')"
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValidationError) as exc_info:
        _check_dependency_cycle("task-a", "task-b", "proj-1")
    assert exc_info.value.code == "DEPENDENCY_CYCLE"


def test_self_dependency(tmp_db):
    """Test that a task depending on itself (A -> A) raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        _check_dependency_cycle("task-a", "task-a", "proj-1")
    assert exc_info.value.code == "DEPENDENCY_CYCLE"


def test_different_project_no_interference(tmp_db):
    """Test that dependencies in a different project are ignored."""
    conn = get_db_connection()
    # B -> A in proj-2.
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, status, depends_on) VALUES "
        "('task-b', 'proj-2', 'Task B', 'todo', 'task-a')"
    )
    conn.commit()
    conn.close()

    # Checking A -> B in proj-1 should be fine because proj-1 is isolated
    _check_dependency_cycle("task-a", "task-b", "proj-1")
