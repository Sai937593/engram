"""Tests for MCP read-only tool handlers."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import yaml

from engram.db import get_db_connection
from engram.models.memory import Memory
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task


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
    assert "engram_memory_search" in server.tools
    assert server.tools["engram_memory_search"].__name__ == "engram_memory_search"
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
    assert "engram_workflow_start" in server.tools
    assert server.tools["engram_workflow_start"].__name__ == "engram_workflow_start"
    assert "engram_workflow_finish" in server.tools
    assert server.tools["engram_workflow_finish"].__name__ == "engram_workflow_finish"


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

    result = yaml.safe_load(handler())
    assert result == {
        "ok": True,
        "project": {
            "id": "proj-tool-1",
            "name": "MCP Tool Project",
            "status": "active",
        },
    }


def test_mcp_tool_raises_project_not_bound_for_unbound_repo(tmp_db, monkeypatch) -> None:
    """Verify engram_project_current returns PROJECT_NOT_BOUND for unbound cwd."""
    cwd = os.path.abspath("repo/unbound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_project_current"]

    result = yaml.safe_load(handler())
    assert result["ok"] is False
    assert result["error"] == "PROJECT_NOT_BOUND"


def test_mcp_tool_memory_search_searches_memories(tmp_db, monkeypatch) -> None:
    """Verify engram_memory_search returns serialized memories for a bound repo."""
    cwd = os.path.abspath("repo/bound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-memories",
        name="MCP Memory Search Project",
        summary="Service tool memory search summary",
        repo_paths=[cwd],
    )
    Memory.create(
        project_id=project.id,
        id="mem-1",
        type="note",
        title="First Memory",
        content="This is the first memory.",
        tags=["important"],
        level="L1",
    )
    Memory.create(
        project_id=project.id,
        id="mem-2",
        type="issue",
        title="Second Memory",
        content="This is the second memory.",
        tags=["issue", "bug"],
        level="L2",
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_memory_search"]

    # All memories
    res_all = yaml.safe_load(handler())
    assert res_all["ok"] is True
    assert len(res_all["memories"]) == 2
    assert {m["id"] for m in res_all["memories"]} == {"mem-1", "mem-2"}

    # Filtered by type
    res_note = yaml.safe_load(handler(type="note"))
    assert res_note["ok"] is True
    assert len(res_note["memories"]) == 1
    assert res_note["memories"][0]["id"] == "mem-1"

    # Search with a query
    res_query = yaml.safe_load(handler(query="second"))
    assert res_query["ok"] is True
    assert len(res_query["memories"]) == 1
    assert res_query["memories"][0]["id"] == "mem-2"

    # Search with tags
    res_tags = yaml.safe_load(handler(tags=["important"]))
    assert res_tags["ok"] is True
    assert len(res_tags["memories"]) == 1
    assert res_tags["memories"][0]["id"] == "mem-1"


def test_mcp_tool_memory_search_raises_project_not_bound(tmp_db, monkeypatch) -> None:
    """Verify engram_memory_search returns PROJECT_NOT_BOUND for unbound cwd."""
    cwd = os.path.abspath("repo/unbound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_memory_search"]

    result = yaml.safe_load(handler())
    assert result["ok"] is False
    assert result["error"] == "PROJECT_NOT_BOUND"


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
    res_all = yaml.safe_load(handler(status="all"))
    assert res_all["ok"] is True
    assert len(res_all["tasks"]) == 2
    assert {t["id"] for t in res_all["tasks"]} == {"task-1", "task-2"}
    assert res_all["hint"] == "Use engram_task_get <id> for full task details"
    for t in res_all["tasks"]:
        assert set(t.keys()) == {"id", "title", "status"}

    # Filtered by status
    res_todo = yaml.safe_load(handler(status="todo"))
    assert res_todo["ok"] is True
    assert len(res_todo["tasks"]) == 1
    assert res_todo["tasks"][0]["id"] == "task-1"

    # Filtered by phase
    res_phase = yaml.safe_load(handler(phase="Task Phase"))
    assert res_phase["ok"] is True
    # By default, status is None, which filters by "todo"
    assert len(res_phase["tasks"]) == 1
    assert res_phase["tasks"][0]["id"] == "task-1"


def test_mcp_tool_task_list_empty(tmp_db, monkeypatch) -> None:
    """Verify task list empty behavior and status filter hint."""
    cwd = os.path.abspath("repo/bound-mcp-tool-empty")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-tool-empty",
        name="MCP Empty Project",
        summary="Empty",
        repo_paths=[cwd],
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_task_list"]

    res = yaml.safe_load(handler(status="todo"))
    assert res == {
        "ok": True,
        "tasks": [],
        "hint": "No todo tasks. Try status=all to see all tasks.",
    }


def test_mcp_tool_task_list_raises_project_not_bound(tmp_db, monkeypatch) -> None:
    """Verify engram_task_list returns PROJECT_NOT_BOUND for unbound cwd."""
    cwd = os.path.abspath("repo/unbound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_task_list"]

    result = yaml.safe_load(handler())
    assert result["ok"] is False
    assert result["error"] == "PROJECT_NOT_BOUND"


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

    res = yaml.safe_load(handler(task_ref="task-get-1"))
    assert res["ok"] is True
    assert res["task"]["id"] == "task-get-1"
    assert res["task"]["title"] == "Task to Get"


def test_mcp_tool_task_get_raises_project_not_bound(tmp_db, monkeypatch) -> None:
    """Verify engram_task_get returns PROJECT_NOT_BOUND for unbound cwd."""
    cwd = os.path.abspath("repo/unbound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_task_get"]

    result = yaml.safe_load(handler(task_ref="task-1"))
    assert result["ok"] is False
    assert result["error"] == "PROJECT_NOT_BOUND"


def test_mcp_tool_task_get_raises_task_not_found(tmp_db, monkeypatch) -> None:
    """Verify engram_task_get returns TASK_NOT_FOUND when task does not exist."""
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

    result = yaml.safe_load(handler(task_ref="missing-task"))
    assert result["ok"] is False
    assert result["error"] == "TASK_NOT_FOUND"


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
    res_none = yaml.safe_load(handler())
    assert res_none["ok"] is True
    assert res_none.get("task") is None

    # Create an active task
    Task.create(
        project_id=project.id,
        id="task-next-1",
        title="Next Actionable Task",
        phase=phase.title,
        phase_id=phase.id,
        status="todo",
    )

    res_task = yaml.safe_load(handler())
    assert res_task["ok"] is True
    assert res_task["task"]["id"] == "task-next-1"
    assert res_task["task"]["title"] == "Next Actionable Task"


def test_mcp_tool_task_next_raises_project_not_bound(tmp_db, monkeypatch) -> None:
    """Verify engram_task_next returns PROJECT_NOT_BOUND for unbound cwd."""
    cwd = os.path.abspath("repo/unbound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_task_next"]

    result = yaml.safe_load(handler())
    assert result["ok"] is False
    assert result["error"] == "PROJECT_NOT_BOUND"


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
    res_all = yaml.safe_load(handler(status="all"))
    assert res_all["ok"] is True
    assert len(res_all["phases"]) == 2
    assert {p["id"] for p in res_all["phases"]} == {"phase-1", "phase-2"}
    for p in res_all["phases"]:
        assert set(p.keys()) == {"id", "title", "status"}

    # Filtered by status
    res_active = yaml.safe_load(handler(status="active"))
    assert res_active["ok"] is True
    assert len(res_active["phases"]) == 1
    assert res_active["phases"][0]["id"] == "phase-2"


def test_mcp_tool_phase_list_raises_project_not_bound(tmp_db, monkeypatch) -> None:
    """Verify engram_phase_list returns PROJECT_NOT_BOUND for unbound cwd."""
    cwd = os.path.abspath("repo/unbound-mcp-tool")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_phase_list"]

    result = yaml.safe_load(handler())
    assert result["ok"] is False
    assert result["error"] == "PROJECT_NOT_BOUND"


def test_mcp_task_create_happy_and_error_paths(tmp_db, monkeypatch) -> None:
    """Verify engram_task_create tool creates a task and gracefully handles service validation errors."""
    cwd = os.path.abspath("repo/bound-mcp-tool-writes")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-writes",
        name="MCP Tool Writes Project",
        summary="Service tool writes summary",
        repo_paths=[cwd],
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    create_handler = server.tools["engram_task_create"]

    # 1. Happy path (no in-progress task)
    res = yaml.safe_load(
        create_handler(
            title="Test Task Title",
            description="Test description",
            priority="high",
            tags=["mcp", "test"],
        )
    )
    assert res["ok"] is True
    assert "id" in res
    assert res["title"] == "Test Task Title"
    assert "task" not in res
    assert "warn" not in res

    # 1b. Happy path with in-progress task already existing (returns warn)
    Task.create(
        project_id=project.id,
        id="ip-task",
        title="Existing Task",
        status="in-progress",
    )
    res_warn = yaml.safe_load(
        create_handler(
            title="Another Task",
        )
    )
    assert res_warn["ok"] is True
    assert "id" in res_warn
    assert res_warn["title"] == "Another Task"
    assert "warn" in res_warn

    # 2. Validation error path (invalid priority)
    res_err = yaml.safe_load(
        create_handler(
            title="Invalid priority task",
            priority="ultra-high",
        )
    )
    assert res_err["ok"] is False
    assert "error" in res_err
    assert res_err["error"] == "INVALID_TASK_PRIORITY"


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
    res = yaml.safe_load(
        update_handler(
            task_ref="task-to-update",
            updates={"title": "Updated Title", "status": "in-progress"},
        )
    )
    assert res["ok"] is True
    assert res["id"] == "task-to-update"
    assert res["updated_fields"] == ["status", "title"]
    assert "task" not in res

    # 2. Validation error path (invalid status)
    res_err = yaml.safe_load(
        update_handler(
            task_ref="task-to-update",
            updates={"status": "not-a-valid-status"},
        )
    )
    assert res_err["ok"] is False
    assert "error" in res_err
    assert res_err["error"] == "INVALID_TASK_STATUS"


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
    res = yaml.safe_load(
        note_handler(
            task_ref="task-for-note",
            note="First important comment",
        )
    )
    assert res["ok"] is True
    assert res["id"] == "task-for-note"
    assert "task" not in res

    # Assert note actually saved to the model
    updated_task = Task.get("task-for-note")
    assert updated_task is not None
    assert "First important comment" in updated_task.evidence

    # 2. Validation error path (empty note)
    res_err = yaml.safe_load(
        note_handler(
            task_ref="task-for-note",
            note="  ",
        )
    )
    assert res_err["ok"] is False
    assert res_err["error"] == "INVALID_NOTE"


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
    res = yaml.safe_load(
        create_handler(
            type="lesson",
            title="Test Lesson Memory",
            content="Test content for lesson",
            scope="project",
            level="L1",
            tags=["mcp", "test"],
        )
    )
    assert res["ok"] is True
    assert "memory" in res
    assert res["memory"]["title"] == "Test Lesson Memory"
    assert res["memory"]["content"] == "Test content for lesson"
    assert res["memory"]["level"] == "L1"
    assert res["memory"]["tags"] == ["mcp", "test"]

    # 2. Validation error path (missing level for project-scoped memory)
    res_err = yaml.safe_load(
        create_handler(
            type="lesson",
            title="Invalid Lesson Memory",
            content="Missing level",
            scope="project",
        )
    )
    assert res_err["ok"] is False
    assert "error" in res_err
    assert res_err["error"] == "INVALID_MEMORY_LEVEL"


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
    res = yaml.safe_load(handler(phase_ref="Phase 1"))
    assert res["ok"] is True
    assert res["phase"]["status"] == "active"

    # 2. Error path (invalid phase_ref)
    res_err = yaml.safe_load(handler(phase_ref="Non-existent Phase"))
    assert res_err["ok"] is False
    assert res_err["error"] == "PHASE_NOT_FOUND"


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
    res_err = yaml.safe_load(handler(phase_ref="Phase 1"))
    assert res_err["ok"] is False
    assert res_err["error"] == "UNFINISHED_TASKS"

    # Complete the task first
    task = Task.get("task-unfinished")
    task.update(status="done")

    # 2. Happy path
    res = yaml.safe_load(handler(phase_ref="Phase 1"))
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
    res_err = yaml.safe_load(handler(task_ref="task-start-1"))
    assert res_err["ok"] is False
    assert res_err["error"] == "DEPENDENCY_UNSATISFIED"

    # Complete dependency
    dep.update(status="done")

    # 2. Happy path
    res = yaml.safe_load(handler(task_ref="task-start-1"))
    assert res["ok"] is True
    assert res["id"] == "task-start-1"
    assert res["status"] == "in-progress"
    assert (
        res["next"]
        == "Run engram_memory_search with task keywords, then draft implementation_plan.md"
    )
    assert "task" not in res


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

    # 1. Happy path (with evidence, phase is complete because no other tasks exist)
    res = yaml.safe_load(handler(task_ref="task-done-1", evidence="Finished successfully!"))
    assert res["ok"] is True
    assert res["id"] == "task-done-1"
    assert res["status"] == "done"
    assert res["phase_complete"] is True
    assert res["next"] == "Log lessons with engram_memory_create, then call engram_workflow_finish"
    assert "task" not in res

    # Assert evidence is saved to model
    updated_task = Task.get("task-done-1")
    assert updated_task is not None
    assert "Finished successfully!" in updated_task.evidence

    # 1b. Happy path (with other unfinished task in same phase -> phase_complete = False)
    Task.create(
        project_id=project.id, id="task-done-2", title="Another Active Task", status="in-progress"
    )
    Task.get("task-done-1").update(status="in-progress")

    res_not_complete = yaml.safe_load(handler(task_ref="task-done-1"))
    assert res_not_complete["ok"] is True
    assert res_not_complete["phase_complete"] is False

    # 2. Error path (non-existent task)
    res_err = yaml.safe_load(handler(task_ref="missing-task"))
    assert res_err["ok"] is False
    assert res_err["error"] == "TASK_NOT_FOUND"


def test_mcp_workflow_tools_happy_and_error_paths(tmp_db, monkeypatch) -> None:
    """Verify that engram_workflow_start and engram_workflow_finish operate correctly under mock conditions."""
    cwd = os.path.abspath("repo/bound-mcp-tool-workflow")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-tool-workflow",
        name="MCP Tool Workflow Project",
        summary="Service tool workflow summary",
        repo_paths=[cwd],
    )

    # Setup mock returns
    mock_start_res = {
        "task": {"id": "t1", "title": "Test Task"},
        "branch": "feat/test",
        "is_resuming": False,
        "context": "Context payload",
    }

    mock_finish_res = {
        "id": "t1",
        "commit": "feat: Test Task",
        "phase_complete": False,
    }

    start_called_args = []

    def dummy_start_workflow(project_id: str, repo_path: str):
        start_called_args.append((project_id, repo_path))
        return mock_start_res

    finish_called_args = []

    def dummy_finish_workflow(project_id: str, repo_path: str, commit_type: str | None = None):
        finish_called_args.append((project_id, repo_path, commit_type))
        return mock_finish_res

    monkeypatch.setattr("engram.mcp.tools.start_workflow", dummy_start_workflow)
    monkeypatch.setattr("engram.mcp.tools.finish_workflow", dummy_finish_workflow)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    start_handler = server.tools["engram_workflow_start"]
    finish_handler = server.tools["engram_workflow_finish"]

    # 1. Happy path: Start (handler is now async)
    res_start = asyncio.run(start_handler())
    assert res_start == "Context payload"
    assert start_called_args == [("proj-tool-workflow", cwd)]

    # 2. Happy path: Finish (handler is now async)
    res_finish = yaml.safe_load(asyncio.run(finish_handler(commit_type="feat")))
    assert res_finish["ok"] is True
    assert res_finish["id"] == "t1"
    assert res_finish["commit"] == "feat: Test Task"
    assert res_finish["phase_complete"] is False
    assert res_finish["next"] == "Run engram_workflow_start to claim the next task."
    assert "task" not in res_finish
    assert "push_output" not in res_finish
    assert finish_called_args == [("proj-tool-workflow", cwd, "feat")]

    # 3. Error path: start_workflow raising EngramServiceError
    from engram.services.errors import EngramServiceError

    def raising_start(project_id, repo_path):
        raise EngramServiceError(code="TEST_ERROR", message="Mock error message")

    monkeypatch.setattr("engram.mcp.tools.start_workflow", raising_start)

    res_err = yaml.safe_load(asyncio.run(start_handler()))
    assert res_err["ok"] is False
    assert res_err["error"] == "TEST_ERROR"
    assert res_err["message"] == "Mock error message"

    # 4. Error path: Project bound but has no repo_paths configured
    monkeypatch.setattr(
        "engram.mcp.tools.resolve_current_project",
        lambda: {"id": "proj-tool-workflow", "repo_paths": []},
    )
    res_no_repo = yaml.safe_load(asyncio.run(start_handler()))
    assert res_no_repo["ok"] is False
    assert res_no_repo["error"] == "PROJECT_NO_REPOS"


def test_mcp_error_responses_contain_correct_fixes(tmp_db, monkeypatch) -> None:
    """Verify that flat YAML error responses include the correct fix field for all known error codes."""
    import yaml

    from engram.mcp.tools import _respond_error
    from engram.services.errors import EngramServiceError

    known_codes = [
        "DEPENDENCY_UNSATISFIED",
        "NO_TASK_IN_PROGRESS",
        "TASK_NOT_FOUND",
        "TASK_AMBIGUOUS",
        "DIRTY_WORKING_TREE",
        "INVALID_TASK_STATUS",
        "PHASE_COMPLETION_BLOCKED",
        "UNFINISHED_TASKS",
    ]

    for code in known_codes:
        exc = EngramServiceError(code=code, message=f"Test error {code}")
        res = yaml.safe_load(_respond_error(exc))
        assert res["ok"] is False
        assert res["error"] == code
        assert res["message"] == f"Test error {code}"
        assert "fix" in res
        assert "engram_" in res["fix"]  # references MCP tool names

    # Unknown/unexpected error should not have fix field
    exc_unknown = EngramServiceError(code="SOME_UNKNOWN_ERROR", message="An unknown error")
    res_unknown = yaml.safe_load(_respond_error(exc_unknown))
    assert res_unknown["ok"] is False
    assert res_unknown["error"] == "SOME_UNKNOWN_ERROR"
    assert "fix" not in res_unknown
