"""Tests for MCP read-only tool handlers."""

from __future__ import annotations

import os
from typing import Any

import pytest

from engram.db import get_db_connection
from engram.models.memory import Memory
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError


class MockServer:
    """Mock FastMCP server for registration and handler testing."""

    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, **kwargs: Any) -> Any:
        """Mock the tool decorator."""

        def decorator(func: Any) -> Any:
            self.tools[func.__name__] = func
            return func

        return decorator


def test_register_tools_registers_engram_project_current() -> None:
    """Verify that register_tools registers the expected tools."""
    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    assert "engram_project_current" in server.tools
    assert server.tools["engram_project_current"].__name__ == "engram_project_current"
    assert "engram_task_list" in server.tools
    assert server.tools["engram_task_list"].__name__ == "engram_task_list"
    assert "engram_task_get" in server.tools
    assert server.tools["engram_task_get"].__name__ == "engram_task_get"
    assert "engram_task_next" in server.tools
    assert server.tools["engram_task_next"].__name__ == "engram_task_next"
    assert "engram_phase_list" in server.tools
    assert server.tools["engram_phase_list"].__name__ == "engram_phase_list"
    assert "engram_task_create" in server.tools
    assert server.tools["engram_task_create"].__name__ == "engram_task_create"
    assert "engram_task_update" in server.tools
    assert server.tools["engram_task_update"].__name__ == "engram_task_update"
    assert "engram_task_note_append" in server.tools
    assert server.tools["engram_task_note_append"].__name__ == "engram_task_note_append"
    assert "engram_memory_create" in server.tools
    assert server.tools["engram_memory_create"].__name__ == "engram_memory_create"
    assert "engram_phase_start" in server.tools
    assert server.tools["engram_phase_start"].__name__ == "engram_phase_start"
    assert "engram_phase_complete" in server.tools
    assert server.tools["engram_phase_complete"].__name__ == "engram_phase_complete"
    assert "engram_task_start" in server.tools
    assert server.tools["engram_task_start"].__name__ == "engram_task_start"
    assert "engram_task_done" in server.tools
    assert server.tools["engram_task_done"].__name__ == "engram_task_done"


def test_mcp_tool_resolves_current_project(tmp_db, monkeypatch) -> None:
    """Verify engram_project_current returns serialized project for a bound repo."""
    cwd = os.path.abspath("repo/bound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-tool-1",
        name="MCP Tool Project",
        summary="Service tool project summary",
        repo_paths=[cwd],
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_project_current"]

    result = handler()
    assert result == {
        "ok": True,
        "project": {
            "id": "proj-tool-1",
            "name": "MCP Tool Project",
            "summary": "Service tool project summary",
            "status": "active",
            "repo_paths": [cwd],
        },
    }


def test_mcp_tool_raises_project_not_bound_for_unbound_repo(tmp_db, monkeypatch) -> None:
    """Verify engram_project_current raises PROJECT_NOT_BOUND for unbound cwd."""
    cwd = os.path.abspath("repo/unbound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_project_current"]

    with pytest.raises(EngramServiceError) as raised:
        handler()

    assert raised.value.code == "PROJECT_NOT_BOUND"


def test_mcp_tool_is_read_only_and_does_not_mutate_db(tmp_db, monkeypatch) -> None:
    """Verify that calling engram_project_current does not mutate database rows."""

    def _table_rows(table_name: str) -> list[dict[str, object]]:
        conn = get_db_connection()
        rows = conn.execute(f"SELECT * FROM {table_name} ORDER BY rowid ASC").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    cwd = os.path.abspath("repo/fake-read-only-tool-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-tool-ro",
        name="MCP Tool Project RO",
        summary="Test project for MCP Tool RO",
        repo_paths=[cwd],
    )
    phase = Phase.create(
        project_id=project.id, id="phase_ro", title="Active phase", status="active"
    )
    Task.create(
        project_id=project.id,
        id="task_ro",
        title="RO Task",
        phase=phase.title,
        phase_id=phase.id,
    )
    Memory.create(
        project_id=project.id,
        id="memo_ro",
        type="note",
        title="RO Memory",
        content="Testing read only tool.",
        tags=["mcp"],
        level="L3",
    )

    before_rows = {
        "projects": _table_rows("projects"),
        "tasks": _table_rows("tasks"),
        "phases": _table_rows("phases"),
        "memories": _table_rows("memories"),
    }

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_project_current"]
    handler()

    handler_tasks = server.tools["engram_task_list"]
    handler_tasks(status="all")

    after_rows = {
        "projects": _table_rows("projects"),
        "tasks": _table_rows("tasks"),
        "phases": _table_rows("phases"),
        "memories": _table_rows("memories"),
    }

    assert after_rows == before_rows


def test_mcp_tool_task_list_lists_tasks(tmp_db, monkeypatch) -> None:
    """Verify engram_task_list returns serialized tasks for a bound repo."""
    cwd = os.path.abspath("repo/bound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-tasks",
        name="MCP Task List Project",
        summary="Service tool tasks summary",
        repo_paths=[cwd],
    )
    phase = Phase.create(
        project_id=project.id,
        id="phase-task-list",
        title="Task Phase",
        status="active",
    )
    Task.create(
        project_id=project.id,
        id="task-1",
        title="First Task",
        phase=phase.title,
        phase_id=phase.id,
        status="todo",
    )
    Task.create(
        project_id=project.id,
        id="task-2",
        title="Second Task",
        phase=phase.title,
        phase_id=phase.id,
        status="in-progress",
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_task_list"]

    # All tasks
    res_all = handler(status="all")
    assert res_all["ok"] is True
    assert len(res_all["tasks"]) == 2
    assert {t["id"] for t in res_all["tasks"]} == {"task-1", "task-2"}

    # Filtered by status
    res_todo = handler(status="todo")
    assert res_todo["ok"] is True
    assert len(res_todo["tasks"]) == 1
    assert res_todo["tasks"][0]["id"] == "task-1"

    # Filtered by phase
    res_phase = handler(phase="Task Phase")
    assert res_phase["ok"] is True
    # By default, status is None, which filters by "todo"
    assert len(res_phase["tasks"]) == 1
    assert res_phase["tasks"][0]["id"] == "task-1"


def test_mcp_tool_task_list_raises_project_not_bound(tmp_db, monkeypatch) -> None:
    """Verify engram_task_list raises PROJECT_NOT_BOUND for unbound cwd."""
    cwd = os.path.abspath("repo/unbound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_task_list"]

    with pytest.raises(EngramServiceError) as raised:
        handler()

    assert raised.value.code == "PROJECT_NOT_BOUND"


def test_mcp_tool_task_get_returns_task(tmp_db, monkeypatch) -> None:
    """Verify engram_task_get returns serialized task details for a bound repo."""
    cwd = os.path.abspath("repo/bound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-tasks-get",
        name="MCP Task Get Project",
        summary="Service tool tasks get summary",
        repo_paths=[cwd],
    )
    phase = Phase.create(
        project_id=project.id,
        id="phase-task-get",
        title="Task Phase",
        status="active",
    )
    Task.create(
        project_id=project.id,
        id="task-get-1",
        title="Task to Get",
        phase=phase.title,
        phase_id=phase.id,
        status="todo",
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_task_get"]

    res = handler(task_ref="task-get-1")
    assert res["ok"] is True
    assert res["task"]["id"] == "task-get-1"
    assert res["task"]["title"] == "Task to Get"


def test_mcp_tool_task_get_raises_project_not_bound(tmp_db, monkeypatch) -> None:
    """Verify engram_task_get raises PROJECT_NOT_BOUND for unbound cwd."""
    cwd = os.path.abspath("repo/unbound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_task_get"]

    with pytest.raises(EngramServiceError) as raised:
        handler(task_ref="task-1")

    assert raised.value.code == "PROJECT_NOT_BOUND"


def test_mcp_tool_task_get_raises_task_not_found(tmp_db, monkeypatch) -> None:
    """Verify engram_task_get raises TASK_NOT_FOUND when task does not exist."""
    cwd = os.path.abspath("repo/bound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-tool-tasks-get-missing",
        name="MCP Task Get Project Missing",
        summary="Service tool tasks get missing summary",
        repo_paths=[cwd],
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_task_get"]

    with pytest.raises(EngramServiceError) as raised:
        handler(task_ref="missing-task")

    assert raised.value.code == "TASK_NOT_FOUND"


def test_mcp_tool_task_next_returns_next_task(tmp_db, monkeypatch) -> None:
    """Verify engram_task_next returns the next actionable task, or None if none exist."""
    cwd = os.path.abspath("repo/bound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-tasks-next",
        name="MCP Task Next Project",
        summary="Service tool tasks next summary",
        repo_paths=[cwd],
    )
    phase = Phase.create(
        project_id=project.id,
        id="phase-task-next",
        title="Task Phase",
        status="active",
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_task_next"]

    # When no tasks exist, returns None
    res_none = handler()
    assert res_none["ok"] is True
    assert res_none["task"] is None

    # Create an active task
    Task.create(
        project_id=project.id,
        id="task-next-1",
        title="Next Actionable Task",
        phase=phase.title,
        phase_id=phase.id,
        status="todo",
    )

    res_task = handler()
    assert res_task["ok"] is True
    assert res_task["task"]["id"] == "task-next-1"
    assert res_task["task"]["title"] == "Next Actionable Task"


def test_mcp_tool_task_next_raises_project_not_bound(tmp_db, monkeypatch) -> None:
    """Verify engram_task_next raises PROJECT_NOT_BOUND for unbound cwd."""
    cwd = os.path.abspath("repo/unbound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_task_next"]

    with pytest.raises(EngramServiceError) as raised:
        handler()

    assert raised.value.code == "PROJECT_NOT_BOUND"


def test_mcp_tool_phase_list_lists_phases(tmp_db, monkeypatch) -> None:
    """Verify engram_phase_list returns serialized phases for a bound repo."""
    cwd = os.path.abspath("repo/bound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-phases",
        name="MCP Phase List Project",
        summary="Service tool phases summary",
        repo_paths=[cwd],
    )
    Phase.create(
        project_id=project.id,
        id="phase-1",
        title="First Phase",
        status="done",
    )
    Phase.create(
        project_id=project.id,
        id="phase-2",
        title="Second Phase",
        status="active",
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_phase_list"]

    # All phases
    res_all = handler(status="all")
    assert res_all["ok"] is True
    assert len(res_all["phases"]) == 2
    assert {p["id"] for p in res_all["phases"]} == {"phase-1", "phase-2"}

    # Filtered by status
    res_active = handler(status="active")
    assert res_active["ok"] is True
    assert len(res_active["phases"]) == 1
    assert res_active["phases"][0]["id"] == "phase-2"


def test_mcp_tool_phase_list_raises_project_not_bound(tmp_db, monkeypatch) -> None:
    """Verify engram_phase_list raises PROJECT_NOT_BOUND for unbound cwd."""
    cwd = os.path.abspath("repo/unbound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_phase_list"]

    with pytest.raises(EngramServiceError) as raised:
        handler()

    assert raised.value.code == "PROJECT_NOT_BOUND"


def test_mcp_task_create_happy_and_error_paths(tmp_db, monkeypatch) -> None:
    """Verify engram_task_create tool creates a task and gracefully handles service validation errors."""
    cwd = os.path.abspath("repo/bound-mcp-tool-writes")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-tool-writes",
        name="MCP Tool Writes Project",
        summary="Service tool writes summary",
        repo_paths=[cwd],
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    create_handler = server.tools["engram_task_create"]

    # 1. Happy path
    res = create_handler(
        title="Test Task Title",
        description="Test description",
        priority="high",
        tags=["mcp", "test"],
    )
    assert res["ok"] is True
    assert "task" in res
    assert res["task"]["title"] == "Test Task Title"
    assert res["task"]["priority"] == "high"
    assert res["task"]["tags"] == ["mcp", "test"]

    # 2. Validation error path (invalid priority)
    res_err = create_handler(
        title="Invalid priority task",
        priority="ultra-high",
    )
    assert res_err["ok"] is False
    assert "error" in res_err
    assert res_err["error"]["code"] == "INVALID_TASK_PRIORITY"


def test_mcp_task_update_happy_and_error_paths(tmp_db, monkeypatch) -> None:
    """Verify engram_task_update tool updates a task and gracefully handles service validation errors."""
    cwd = os.path.abspath("repo/bound-mcp-tool-writes")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-writes",
        name="MCP Tool Writes Project",
        summary="Service tool writes summary",
        repo_paths=[cwd],
    )

    # Pre-populate task
    Task.create(
        project_id=project.id,
        id="task-to-update",
        title="Original Title",
        status="todo",
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    update_handler = server.tools["engram_task_update"]

    # 1. Happy path
    res = update_handler(
        task_ref="task-to-update",
        updates={"title": "Updated Title", "status": "in-progress"},
    )
    assert res["ok"] is True
    assert res["task"]["title"] == "Updated Title"
    assert res["task"]["status"] == "in-progress"

    # 2. Validation error path (invalid status)
    res_err = update_handler(
        task_ref="task-to-update",
        updates={"status": "not-a-valid-status"},
    )
    assert res_err["ok"] is False
    assert res_err["error"]["code"] == "INVALID_TASK_STATUS"


def test_mcp_task_note_append_happy_and_error_paths(tmp_db, monkeypatch) -> None:
    """Verify engram_task_note_append tool appends notes and gracefully handles service validation errors."""
    cwd = os.path.abspath("repo/bound-mcp-tool-writes")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-writes",
        name="MCP Tool Writes Project",
        summary="Service tool writes summary",
        repo_paths=[cwd],
    )

    Task.create(
        project_id=project.id,
        id="task-for-note",
        title="Note Task",
        status="todo",
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    note_handler = server.tools["engram_task_note_append"]

    # 1. Happy path
    res = note_handler(
        task_ref="task-for-note",
        note="First important comment",
    )
    assert res["ok"] is True
    assert "First important comment" in res["task"]["evidence"]

    # 2. Validation error path (empty note)
    res_err = note_handler(
        task_ref="task-for-note",
        note="  ",
    )
    assert res_err["ok"] is False
    assert res_err["error"]["code"] == "INVALID_NOTE"


def test_mcp_memory_create_happy_and_error_paths(tmp_db, monkeypatch) -> None:
    """Verify engram_memory_create tool creates a memory and gracefully handles service validation errors."""
    cwd = os.path.abspath("repo/bound-mcp-tool-writes")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-tool-writes",
        name="MCP Tool Writes Project",
        summary="Service tool writes summary",
        repo_paths=[cwd],
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    create_handler = server.tools["engram_memory_create"]

    # 1. Happy path
    res = create_handler(
        type="lesson",
        title="Test Lesson Memory",
        content="Test content for lesson",
        scope="project",
        level="L1",
        tags=["mcp", "test"],
    )
    assert res["ok"] is True
    assert "memory" in res
    assert res["memory"]["title"] == "Test Lesson Memory"
    assert res["memory"]["content"] == "Test content for lesson"
    assert res["memory"]["level"] == "L1"
    assert res["memory"]["tags"] == ["mcp", "test"]

    # 2. Validation error path (missing level for project-scoped memory)
    res_err = create_handler(
        type="lesson",
        title="Invalid Lesson Memory",
        content="Missing level",
        scope="project",
    )
    assert res_err["ok"] is False
    assert "error" in res_err
    assert res_err["error"]["code"] == "INVALID_MEMORY_LEVEL"


def test_mcp_phase_start_happy_and_error_paths(tmp_db, monkeypatch) -> None:
    """Verify engram_phase_start tool starts a phase and gracefully handles errors."""
    cwd = os.path.abspath("repo/bound-mcp-tool-writes")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-writes",
        name="MCP Tool Writes Project",
        summary="Service tool writes summary",
        repo_paths=[cwd],
    )
    Phase.create(project_id=project.id, id="ph-start-1", title="Phase 1", status="planned")

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    handler = server.tools["engram_phase_start"]

    # 1. Happy path
    res = handler(phase_ref="Phase 1")
    assert res["ok"] is True
    assert res["phase"]["status"] == "active"

    # 2. Error path (invalid phase_ref)
    res_err = handler(phase_ref="Non-existent Phase")
    assert res_err["ok"] is False
    assert res_err["error"]["code"] == "PHASE_NOT_FOUND"


def test_mcp_phase_complete_happy_and_error_paths(tmp_db, monkeypatch) -> None:
    """Verify engram_phase_complete tool completes a phase and handles validation errors."""
    cwd = os.path.abspath("repo/bound-mcp-tool-writes")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-writes",
        name="MCP Tool Writes Project",
        summary="Service tool writes summary",
        repo_paths=[cwd],
    )
    phase = Phase.create(project_id=project.id, id="ph-comp-1", title="Phase 1", status="active")

    # Add unfinished task to trigger validation error
    Task.create(
        project_id=project.id,
        id="task-unfinished",
        title="Unfinished Task",
        phase_id=phase.id,
        status="todo",
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    handler = server.tools["engram_phase_complete"]

    # 1. Error path (unfinished tasks exist)
    res_err = handler(phase_ref="Phase 1")
    assert res_err["ok"] is False
    assert res_err["error"]["code"] == "UNFINISHED_TASKS"

    # Complete the task first
    task = Task.get("task-unfinished")
    task.update(status="done")

    # 2. Happy path
    res = handler(phase_ref="Phase 1")
    assert res["ok"] is True
    assert res["phase"]["status"] == "done"


def test_mcp_task_start_happy_and_error_paths(tmp_db, monkeypatch) -> None:
    """Verify engram_task_start tool starts a task and handles validation/dependency errors."""
    cwd = os.path.abspath("repo/bound-mcp-tool-writes")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-writes",
        name="MCP Tool Writes Project",
        summary="Service tool writes summary",
        repo_paths=[cwd],
    )
    # Pre-populate dependency and target task
    dep = Task.create(project_id=project.id, id="task-dep", title="Dependency Task", status="todo")
    Task.create(
        project_id=project.id,
        id="task-start-1",
        title="Target Task",
        status="todo",
        depends_on=dep.id,
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    handler = server.tools["engram_task_start"]

    # 1. Error path (dependency not satisfied)
    res_err = handler(task_ref="task-start-1")
    assert res_err["ok"] is False
    assert res_err["error"]["code"] == "DEPENDENCY_UNSATISFIED"

    # Complete dependency
    dep.update(status="done")

    # 2. Happy path
    res = handler(task_ref="task-start-1")
    assert res["ok"] is True
    assert res["task"]["status"] == "in-progress"


def test_mcp_task_done_happy_and_error_paths(tmp_db, monkeypatch) -> None:
    """Verify engram_task_done tool completes a task with optional evidence."""
    cwd = os.path.abspath("repo/bound-mcp-tool-writes")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-writes",
        name="MCP Tool Writes Project",
        summary="Service tool writes summary",
        repo_paths=[cwd],
    )
    Task.create(project_id=project.id, id="task-done-1", title="Done Task", status="in-progress")

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    handler = server.tools["engram_task_done"]

    # 1. Happy path (with evidence)
    res = handler(task_ref="task-done-1", evidence="Finished successfully!")
    assert res["ok"] is True
    assert res["task"]["status"] == "done"
    assert "Finished successfully!" in res["task"]["evidence"]

    # 2. Error path (non-existent task)
    res_err = handler(task_ref="missing-task")
    assert res_err["ok"] is False
    assert res_err["error"]["code"] == "TASK_NOT_FOUND"
