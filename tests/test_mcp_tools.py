"""Tests for MCP read-only tool handlers."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import pytest
import yaml

from engram.db import get_db_connection
from engram.models.memory import Memory
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task


@pytest.fixture(autouse=True)
def bypass_strict_task_validation(monkeypatch):
    import engram.services.task.crud as crud
    import engram.services.task.validation as validation
    monkeypatch.setattr(validation, "validate_executable_task_metadata", lambda **kwargs: None)
    monkeypatch.setattr(crud, "_validate_executable_task_metadata", lambda **kwargs: None)


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
    assert "engram_project_init" in server.tools
    assert server.tools["engram_project_init"].__name__ == "engram_project_init"
    assert "engram_project_diagnostics" in server.tools
    assert server.tools["engram_project_diagnostics"].__name__ == "engram_project_diagnostics"
    assert "engram_task_list" in server.tools
    assert server.tools["engram_task_list"].__name__ == "engram_task_list"
    assert "engram_task_get" in server.tools
    assert server.tools["engram_task_get"].__name__ == "engram_task_get"
    assert "engram_task_next" in server.tools
    assert server.tools["engram_task_next"].__name__ == "engram_task_next"
    assert "engram_phase_list" in server.tools
    assert server.tools["engram_phase_list"].__name__ == "engram_phase_list"
    assert "engram_phase_create" in server.tools
    assert server.tools["engram_phase_create"].__name__ == "engram_phase_create"
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
    assert "engram_memory_get" in server.tools
    assert server.tools["engram_memory_get"].__name__ == "engram_memory_get"
    assert "engram_memory_update" in server.tools
    assert server.tools["engram_memory_update"].__name__ == "engram_memory_update"
    assert "engram_memory_supersede" in server.tools
    assert server.tools["engram_memory_supersede"].__name__ == "engram_memory_supersede"
    assert "engram_memory_demote" in server.tools
    assert server.tools["engram_memory_demote"].__name__ == "engram_memory_demote"
    assert "engram_memory_archive" in server.tools
    assert server.tools["engram_memory_archive"].__name__ == "engram_memory_archive"
    assert "engram_memory_delete" in server.tools
    assert server.tools["engram_memory_delete"].__name__ == "engram_memory_delete"
    assert "engram_phase_start" in server.tools
    assert server.tools["engram_phase_start"].__name__ == "engram_phase_start"
    assert "engram_phase_complete" in server.tools
    assert server.tools["engram_phase_complete"].__name__ == "engram_phase_complete"
    assert "engram_phase_update" in server.tools
    assert server.tools["engram_phase_update"].__name__ == "engram_phase_update"
    assert "engram_phase_cancel" in server.tools
    assert server.tools["engram_phase_cancel"].__name__ == "engram_phase_cancel"
    assert "engram_phase_archive" in server.tools
    assert server.tools["engram_phase_archive"].__name__ == "engram_phase_archive"
    assert "engram_task_start" in server.tools
    assert server.tools["engram_task_start"].__name__ == "engram_task_start"
    assert "engram_task_done" in server.tools
    assert server.tools["engram_task_done"].__name__ == "engram_task_done"
    assert "engram_task_block" in server.tools
    assert server.tools["engram_task_block"].__name__ == "engram_task_block"
    assert "engram_task_unblock" in server.tools
    assert server.tools["engram_task_unblock"].__name__ == "engram_task_unblock"
    assert "engram_task_cancel" in server.tools
    assert server.tools["engram_task_cancel"].__name__ == "engram_task_cancel"
    assert "engram_task_retire" in server.tools
    assert server.tools["engram_task_retire"].__name__ == "engram_task_retire"
    assert "engram_workflow_start" in server.tools
    assert server.tools["engram_workflow_start"].__name__ == "engram_workflow_start"
    assert "engram_workflow_finish" in server.tools
    assert server.tools["engram_workflow_finish"].__name__ == "engram_workflow_finish"
    assert "engram_workflow_verify" in server.tools
    assert server.tools["engram_workflow_verify"].__name__ == "engram_workflow_verify"


def test_mcp_tool_resolves_current_project(tmp_path, monkeypatch) -> None:
    """Verify engram_project_current returns serialized project for a bound repo."""
    repo_path = tmp_path / "bound_mcp_tool"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    (repo_path / ".engram").mkdir()
    monkeypatch.setattr("os.getcwd", lambda: str(repo_path))

    from engram.db import get_db_connection, init_db

    db_path = repo_path / ".engram" / "memory.db"
    init_db(db_path)
    conn = get_db_connection(db_path)
    conn.execute(
        "INSERT INTO projects (id, name, summary, status, repo_paths) VALUES (?, ?, ?, ?, ?)",
        ("proj-tool-1", "MCP Tool Project", "Service tool project summary", "active", "[]"),
    )
    conn.commit()
    conn.close()

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_project_current"]

    result = yaml.safe_load(handler())
    assert result["ok"] is True
    assert result["initialized"] is True
    assert result["status"] == "ready"
    assert result["project"] == {
        "id": "proj-tool-1",
        "name": "MCP Tool Project",
        "status": "active",
    }


def test_mcp_tool_returns_actionable_uninitialized_for_unbound_repo(tmp_path, monkeypatch) -> None:
    """Verify engram_project_current returns actionable uninitialized status for unbound cwd."""
    repo_path = tmp_path / "unbound_mcp_tool"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    monkeypatch.setattr("os.getcwd", lambda: str(repo_path))

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_project_current"]

    result = yaml.safe_load(handler())
    assert result["ok"] is True
    assert result["initialized"] is False
    assert result["status"] in {"uninitialized", "unresolved-workspace"}
    assert "next" in result


def test_mcp_project_diagnostics_reports_misconfigured_missing_gitignore_entry(
    tmp_path, monkeypatch
) -> None:
    """Verify engram_project_diagnostics reports missing .engram gitignore entry."""
    repo_path = tmp_path / "diag_missing_gitignore_entry"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    (repo_path / ".engram").mkdir()
    (repo_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
    monkeypatch.setattr("os.getcwd", lambda: str(repo_path))

    from engram.db import init_db

    init_db(repo_path / ".engram" / "memory.db")

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_project_diagnostics"]
    result = yaml.safe_load(handler())

    assert result["ok"] is True
    assert result["status"] == "misconfigured"
    assert result["repo_root_detected"] is True
    assert result["gitignore"]["status"] == "missing-entry"
    assert "engram_project_init" in result["next_action"]


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
    assert "## Memory Search" in res_all["result"]
    assert len(res_all["memories"]) == 2
    assert {m["id"] for m in res_all["memories"]} == {"mem-1", "mem-2"}
    assert res_all["hint"] == "Apply these issues/notes before drafting your implementation plan."

    # Filtered by type
    res_note = yaml.safe_load(handler(type="note"))
    assert res_note["ok"] is True
    assert len(res_note["memories"]) == 1
    assert res_note["memories"][0]["id"] == "mem-1"
    assert res_note["hint"] == "Apply these notes before drafting your implementation plan."

    # Search with a query
    res_query = yaml.safe_load(handler(query="second"))
    assert res_query["ok"] is True
    assert len(res_query["memories"]) == 1
    assert res_query["memories"][0]["id"] == "mem-2"
    assert res_query["hint"] == "Apply these issues before drafting your implementation plan."

    # Search with tags
    res_tags = yaml.safe_load(handler(tags=["important"]))
    assert res_tags["ok"] is True
    assert len(res_tags["memories"]) == 1
    assert res_tags["memories"][0]["id"] == "mem-1"
    assert res_tags["hint"] == "Apply these notes before drafting your implementation plan."

    # Search with query that returns no results (miss case)
    res_miss = yaml.safe_load(handler(query="nonexistent"))
    assert res_miss["ok"] is True
    assert res_miss["memories"] == []
    assert "No matching memories found." in res_miss["result"]
    assert (
        res_miss["hint"]
        == "No results. Try broader terms. Log key discoveries with engram_memory_create."
    )


def test_mcp_memory_lifecycle_tools_happy_and_safe_failure(tmp_db, monkeypatch) -> None:
    """Verify memory lifecycle MCP tools delegate to service APIs with safe guidance."""
    cwd = os.path.abspath("repo/bound-mcp-memory-lifecycle")
    monkeypatch.setattr("os.getcwd", lambda: cwd)
    project = Project.create(
        id="proj-tool-memory-lifecycle",
        name="MCP Memory Lifecycle Project",
        summary="Lifecycle coverage",
        repo_paths=[cwd],
    )
    Memory.create(
        project_id=project.id,
        id="mem-lifecycle-source",
        type="decision",
        title="Original decision",
        content="Original content",
        tags=["core"],
        level="L1",
    )
    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    get_tool = server.tools["engram_memory_get"]
    update_tool = server.tools["engram_memory_update"]
    supersede_tool = server.tools["engram_memory_supersede"]
    demote_tool = server.tools["engram_memory_demote"]
    archive_tool = server.tools["engram_memory_archive"]
    delete_tool = server.tools["engram_memory_delete"]

    got = yaml.safe_load(get_tool(memory_ref="mem-lifecycle-source"))
    assert got["ok"] is True
    assert got["memory"]["id"] == "mem-lifecycle-source"

    updated = yaml.safe_load(
        update_tool(memory_ref="mem-lifecycle-source", updates={"title": "Updated decision"})
    )
    assert updated["ok"] is True
    assert updated["memory"]["title"] == "Updated decision"

    superseded = yaml.safe_load(
        supersede_tool(
            memory_ref="mem-lifecycle-source",
            title="Replacement decision",
            content="Replacement content",
        )
    )
    assert superseded["ok"] is True
    source_after_supersede = yaml.safe_load(get_tool(memory_ref="mem-lifecycle-source"))
    assert source_after_supersede["memory"]["superseded_by"] == superseded["memory"]["id"]

    demoted = yaml.safe_load(
        demote_tool(memory_ref=superseded["memory"]["id"], reason="Lower priority")
    )
    assert demoted["ok"] is True
    assert demoted["memory"]["level"] == "L2"

    archived = yaml.safe_load(archive_tool(memory_ref=superseded["memory"]["id"]))
    assert archived["ok"] is True
    assert archived["memory"]["superseded_by"] == superseded["memory"]["id"]

    Memory.create(
        project_id=project.id,
        id="mem-active-delete-blocked",
        type="note",
        title="Active memory",
        content="should require force",
        tags=[],
        level="L2",
    )
    blocked_delete = yaml.safe_load(delete_tool(memory_ref="mem-active-delete-blocked"))
    assert blocked_delete["ok"] is False
    assert blocked_delete["error"] == "MEMORY_DELETE_REQUIRES_FORCE"

    forced_delete = yaml.safe_load(delete_tool(memory_ref="mem-active-delete-blocked", force=True))
    assert forced_delete["ok"] is True
    assert forced_delete["deleted"] is True


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
        status="ready",
    )
    Task.create(
        project_id=project.id,
        id="task-2",
        title="Second Task",
        phase=phase.title,
        phase_id=phase.id,
        status="in_progress",
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
    res_ready = yaml.safe_load(handler(status="ready"))
    assert res_ready["ok"] is True
    assert len(res_ready["tasks"]) == 1
    assert res_ready["tasks"][0]["id"] == "task-1"

    # Filtered by phase
    res_phase = yaml.safe_load(handler(phase="Task Phase"))
    assert res_phase["ok"] is True
    # By default, status is None, which filters by "ready"
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
        status="ready",
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
        status="in_progress",
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

    # 3. Update task to open status successfully
    res_ready = yaml.safe_load(
        update_handler(
            task_ref="task-to-update",
            updates={"status": "open"},
        )
    )
    assert res_ready["ok"] is True
    assert res_ready["id"] == "task-to-update"

    # 5. Memory review outcome happy path
    res_mro = yaml.safe_load(
        update_handler(
            task_ref="task-to-update",
            updates={"memory_review_outcome": "created"},
        )
    )
    assert res_mro["ok"] is True
    assert res_mro["id"] == "task-to-update"
    assert res_mro["updated_fields"] == ["memory_review_outcome"]

    # 6. Memory review outcome no_change path
    res_mro_no_change = yaml.safe_load(
        update_handler(
            task_ref="task-to-update",
            updates={"memory_review_outcome": "no_change"},
        )
    )
    assert res_mro_no_change["ok"] is True
    assert res_mro_no_change["id"] == "task-to-update"
    assert res_mro_no_change["updated_fields"] == ["memory_review_outcome"]

    # 7. Memory review outcome invalid value rejection
    res_mro_err = yaml.safe_load(
        update_handler(
            task_ref="task-to-update",
            updates={"memory_review_outcome": "invalid-outcome-value"},
        )
    )
    assert res_mro_err["ok"] is False
    assert "error" in res_mro_err
    assert res_mro_err["error"] == "INVALID_MEMORY_REVIEW_OUTCOME"


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
    assert "id" in res
    assert res["type"] == "lesson"
    assert "memory" not in res

    # Verify memory was actually saved to database
    from engram.models.memory import Memory

    saved_memory = Memory.get(res["id"])
    assert saved_memory is not None
    assert saved_memory.title == "Test Lesson Memory"
    assert saved_memory.content == "Test content for lesson"
    assert saved_memory.level == "L1"
    assert saved_memory.tags == ["mcp", "test"]

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


def test_mcp_phase_lifecycle_maintenance_tools_happy_and_error_paths(tmp_db, monkeypatch) -> None:
    """Verify engram_phase_update/cancel/archive tools delegate lifecycle behavior safely."""
    cwd = os.path.abspath("repo/bound-mcp-phase-maintenance")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-phase-maint",
        name="MCP Phase Maintenance Project",
        summary="Phase lifecycle maintenance coverage",
        repo_paths=[cwd],
    )
    phase = Phase.create(
        project_id=project.id,
        id="pha-maint-1",
        title="Lifecycle Phase",
        description="Initial description",
        status="active",
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    update_handler = server.tools["engram_phase_update"]
    cancel_handler = server.tools["engram_phase_cancel"]
    archive_handler = server.tools["engram_phase_archive"]

    updated = yaml.safe_load(
        update_handler(
            phase_ref=phase.id,
            title="Lifecycle Phase Updated",
            description="Refined description",
            acceptance="Clear acceptance criteria",
            evidence="Captured verification evidence",
        )
    )
    assert updated["ok"] is True
    assert updated["phase"]["title"] == "Lifecycle Phase Updated"
    assert updated["phase"]["description"] == "Refined description"

    from engram.models.task import Task

    Task.create(
        project_id=project.id,
        id="task-phase-blocker",
        title="Unfinished blocker task",
        phase_id=phase.id,
        status="todo",
    )
    cancelled_err = yaml.safe_load(cancel_handler(phase_ref=phase.id, reason="No longer needed"))
    assert cancelled_err["ok"] is False
    assert cancelled_err["error"] == "UNFINISHED_TASKS"
    assert "fix" in cancelled_err

    blocker = Task.get("task-phase-blocker")
    blocker.update(status="done")
    cancelled = yaml.safe_load(cancel_handler(phase_ref=phase.id, reason="No longer needed"))
    assert cancelled["ok"] is True
    assert cancelled["phase"]["status"] == "cancelled"

    archived = yaml.safe_load(archive_handler(phase_ref=phase.id))
    assert archived["ok"] is True
    assert archived["archived"] is True
    assert archived["phase"]["id"] == phase.id

    archived_err = yaml.safe_load(archive_handler(phase_ref=phase.id))
    assert archived_err["ok"] is False
    assert archived_err["error"] == "PHASE_NOT_FOUND"
    assert "fix" in archived_err


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
    dep = Task.create(project_id=project.id, id="task-dep", title="Dependency Task", status="open")
    Task.create(
        project_id=project.id,
        id="task-start-1",
        title="Target Task",
        status="open",
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
    assert res["status"] == "in_progress"
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


def test_mcp_task_maintenance_lifecycle_tools(tmp_db, monkeypatch) -> None:
    """Verify task block/unblock/cancel/retire MCP tools delegate to services with compact output."""
    cwd = os.path.abspath("repo/bound-mcp-tool-maintenance")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-tool-maintenance",
        name="MCP Task Maintenance Project",
        summary="Service tool task maintenance summary",
        repo_paths=[cwd],
    )
    Task.create(project_id=project.id, id="task-block-1", title="Blockable Task", status="open")
    Task.create(project_id=project.id, id="task-cancel-1", title="Cancelable Task", status="open")
    Task.create(project_id=project.id, id="task-retire-1", title="Retirable Task", status="done")

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    block_handler = server.tools["engram_task_block"]
    unblock_handler = server.tools["engram_task_unblock"]
    cancel_handler = server.tools["engram_task_cancel"]
    retire_handler = server.tools["engram_task_retire"]

    blocked = yaml.safe_load(block_handler(task_ref="task-block-1", reason="Waiting on dependency"))
    assert blocked == {"ok": True, "id": "task-block-1", "status": "blocked"}

    invalid_unblock = yaml.safe_load(
        unblock_handler(task_ref="task-block-1", target_status="in_progress")
    )
    assert invalid_unblock["ok"] is False
    assert invalid_unblock["error"] == "INVALID_TASK_TRANSITION_TARGET"
    assert "engram_task_unblock" in invalid_unblock["fix"]

    unblocked = yaml.safe_load(
        unblock_handler(task_ref="task-block-1", target_status="open", note="Dependency resolved")
    )
    assert unblocked == {"ok": True, "id": "task-block-1", "status": "open"}

    cancelled = yaml.safe_load(cancel_handler(task_ref="task-cancel-1", reason="No longer needed"))
    assert cancelled == {"ok": True, "id": "task-cancel-1", "status": "cancelled"}

    invalid_retire = yaml.safe_load(retire_handler(task_ref="task-block-1"))
    assert invalid_retire["ok"] is False
    assert invalid_retire["error"] == "INVALID_TASK_TRANSITION"
    assert "valid lifecycle tool" in invalid_retire["fix"]

    retired = yaml.safe_load(retire_handler(task_ref="task-retire-1", reason="Cleanup"))
    assert retired == {"ok": True, "deleted": True, "id": "task-retire-1", "status": "done"}
    assert Task.get("task-retire-1") is None


def test_mcp_workflow_tools_happy_and_error_paths(tmp_db, monkeypatch) -> None:
    """Verify workflow start/finish/verify tools operate correctly under mock conditions."""
    cwd = os.path.abspath("repo/bound-mcp-tool-workflow")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-tool-workflow",
        name="MCP Tool Workflow Project",
        summary="Service tool workflow summary",
        repo_paths=[cwd],
    )
    Task.create(
        project_id="proj-tool-workflow",
        id="t-in-progress",
        title="Verification-gated task",
        status="in-progress",
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
        "memory_review_outcome": "created",
    }
    mock_verify_res = {
        "task_id": "t1",
        "task_title": "Test Task",
        "passed": False,
        "summary": "`uv run pytest tests -q` failed. First actionable target: `tests/test_fail.py::test_x`.",
    }

    start_called_args = []

    def dummy_start_workflow(project_id: str, repo_path: str):
        start_called_args.append((project_id, repo_path))
        return mock_start_res

    finish_called_args = []

    def dummy_finish_workflow(project_id: str, repo_path: str, commit_type: str | None = None):
        finish_called_args.append((project_id, repo_path, commit_type))
        return mock_finish_res

    verify_called_args = []

    def dummy_verify_workflow(project_id: str, repo_path: str):
        verify_called_args.append((project_id, repo_path))
        return mock_verify_res

    monkeypatch.setattr("engram.mcp.tools.start_workflow", dummy_start_workflow)
    monkeypatch.setattr("engram.mcp.tools.finish_workflow", dummy_finish_workflow)
    monkeypatch.setattr("engram.mcp.tools.verify_workflow", dummy_verify_workflow)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    start_handler = server.tools["engram_workflow_start"]
    finish_handler = server.tools["engram_workflow_finish"]
    verify_handler = server.tools["engram_workflow_verify"]

    # 1. Happy path: Start (handler is now async)
    res_start = asyncio.run(start_handler())
    assert res_start == "Context payload"
    assert start_called_args == [("proj-tool-workflow", cwd)]

    # 2. Happy path: Finish (handler is now async)
    res_finish = asyncio.run(finish_handler(commit_type="feat"))
    assert "# Task Finished" in res_finish
    assert "Task: `t1`" in res_finish
    assert "Commit: `feat: Test Task`" in res_finish
    assert "Phase complete: False" in res_finish
    assert "Memory review outcome: `created`" in res_finish
    assert "## Next action" in res_finish
    assert (
        "Stop here. The active task is finished and committed. Await further instructions."
        in res_finish
    )
    assert finish_called_args == [("proj-tool-workflow", cwd, "feat")]

    # 3. Happy path: Verify returns compact markdown with one next action
    res_verify = asyncio.run(verify_handler())
    assert "# Verification Result" in res_verify
    assert "Task: `t1` - Test Task" in res_verify
    assert "Status: FAILED" in res_verify
    assert "## Details" in res_verify
    assert mock_verify_res["summary"] in res_verify
    assert "## Next action" in res_verify
    assert res_verify.count("## Next action") == 1
    assert "Fix the first actionable target, then rerun engram_workflow_verify." in res_verify
    assert "ok:" not in res_verify.lower()
    assert "error:" not in res_verify.lower()
    assert verify_called_args == [("proj-tool-workflow", cwd)]

    # 3b. Happy path: Verify PASS remains concise and deterministic
    mock_verify_res["passed"] = True
    mock_verify_res["summary"] = "All local quality checks passed."
    res_verify_pass = asyncio.run(verify_handler())
    assert "# Verification Result" in res_verify_pass
    assert "Task: `t1` - Test Task" in res_verify_pass
    assert "Status: PASSED" in res_verify_pass
    assert "## Details" in res_verify_pass
    assert "All local quality checks passed." in res_verify_pass
    assert "## Next action" in res_verify_pass
    assert res_verify_pass.count("## Next action") == 1
    assert (
        "Verification passed. Continue implementation and run engram_workflow_finish when ready."
        in res_verify_pass
    )

    # 4. Error path: start_workflow raising EngramServiceError
    from engram.services.errors import EngramServiceError

    def raising_start(project_id, repo_path):
        raise EngramServiceError(code="TEST_ERROR", message="Mock error message")

    monkeypatch.setattr("engram.mcp.tools.start_workflow", raising_start)

    res_err = yaml.safe_load(asyncio.run(start_handler()))
    assert res_err["ok"] is False
    assert res_err["error"] == "TEST_ERROR"
    assert res_err["message"] == "Mock error message"

    # 4b. Error path: finish_workflow verification gate returns compact blocked markdown
    def raising_finish_verification(project_id, repo_path, commit_type=None):
        raise EngramServiceError(
            code="VERIFICATION_MISSING",
            message="No verification record exists for the active task.",
        )

    monkeypatch.setattr("engram.mcp.tools.finish_workflow", raising_finish_verification)
    res_finish_blocked = asyncio.run(finish_handler(commit_type="feat"))
    assert "# Finish Blocked" in res_finish_blocked
    assert "Task: `t-in-progress` - Verification-gated task" in res_finish_blocked
    assert "Reason: No verification record exists for the active task." in res_finish_blocked
    assert "## Next action" in res_finish_blocked
    assert res_finish_blocked.count("## Next action") == 1
    assert (
        "Run or rerun engram_workflow_verify, then call engram_workflow_finish again."
        in res_finish_blocked
    )
    assert "ok:" not in res_finish_blocked.lower()
    assert "error:" not in res_finish_blocked.lower()

    # 4c. Error path: finish_workflow verification failed returns compact blocked markdown
    def raising_finish_failed(project_id, repo_path, commit_type=None):
        raise EngramServiceError(
            code="VERIFICATION_FAILED",
            message="The latest verification for the active task failed.",
        )

    monkeypatch.setattr("engram.mcp.tools.finish_workflow", raising_finish_failed)
    res_finish_failed = asyncio.run(finish_handler(commit_type="feat"))
    assert "# Finish Blocked" in res_finish_failed
    assert "Task: `t-in-progress` - Verification-gated task" in res_finish_failed
    assert "Reason: The latest verification for the active task failed." in res_finish_failed
    assert "## Next action" in res_finish_failed
    assert res_finish_failed.count("## Next action") == 1
    assert (
        "Run or rerun engram_workflow_verify, then call engram_workflow_finish again."
        in res_finish_failed
    )

    # 4d. Error path: finish_workflow verification stale returns compact blocked markdown
    def raising_finish_stale(project_id, repo_path, commit_type=None):
        raise EngramServiceError(
            code="VERIFICATION_STALE_RELEVANT_CHANGES",
            message="Relevant files changed after the latest successful verification.",
        )

    monkeypatch.setattr("engram.mcp.tools.finish_workflow", raising_finish_stale)
    res_finish_stale = asyncio.run(finish_handler(commit_type="feat"))
    assert "# Finish Blocked" in res_finish_stale
    assert "Task: `t-in-progress` - Verification-gated task" in res_finish_stale
    assert (
        "Reason: Relevant files changed after the latest successful verification."
        in res_finish_stale
    )
    assert "## Next action" in res_finish_stale
    assert res_finish_stale.count("## Next action") == 1
    assert (
        "Run or rerun engram_workflow_verify, then call engram_workflow_finish again."
        in res_finish_stale
    )

    # 4e. Error path: missing memory review outcome returns compact blocked markdown
    def raising_finish_memory_review_missing(project_id, repo_path, commit_type=None):
        raise EngramServiceError(
            code="MEMORY_REVIEW_OUTCOME_MISSING",
            message="Active task is missing memory_review_outcome.",
        )

    monkeypatch.setattr("engram.mcp.tools.finish_workflow", raising_finish_memory_review_missing)
    res_finish_memory_blocked = asyncio.run(finish_handler(commit_type="feat"))
    assert "# Finish Blocked" in res_finish_memory_blocked
    assert "Task: `t-in-progress` - Verification-gated task" in res_finish_memory_blocked
    assert "Reason: Active task is missing memory_review_outcome." in res_finish_memory_blocked
    assert "## Next action" in res_finish_memory_blocked
    assert res_finish_memory_blocked.count("## Next action") == 1
    assert (
        "Record memory_review_outcome on the active task via engram_task_update, then call "
        "engram_workflow_finish again." in res_finish_memory_blocked
    )

    # 5. Error path: Project bound but has no repo_paths configured
    monkeypatch.setattr(
        "engram.mcp.tools.resolve_current_project",
        lambda: {"id": "proj-tool-workflow", "repo_paths": []},
    )
    res_no_repo = yaml.safe_load(asyncio.run(start_handler()))
    assert res_no_repo["ok"] is False
    assert res_no_repo["error"] == "PROJECT_NO_REPOS"

    res_verify_no_repo = yaml.safe_load(asyncio.run(verify_handler()))
    assert res_verify_no_repo["ok"] is False
    assert res_verify_no_repo["error"] == "PROJECT_NO_REPOS"


def test_mcp_workflow_start_returns_compact_blocked_markdown_for_draft_only(tmp_db, monkeypatch):
    """Verify engram_workflow_start emits Start Blocked markdown when only draft tasks remain."""
    cwd = os.path.abspath("repo/bound-mcp-tool-workflow-draft-only")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-tool-workflow-draft-only",
        name="MCP Tool Workflow Draft-Only Project",
        summary="Service tool workflow summary",
        repo_paths=[cwd],
    )

    from engram.services.errors import EngramServiceError

    def raising_start_draft_only(project_id, repo_path):
        raise EngramServiceError(
            code="WORKFLOW_START_DRAFT_ONLY",
            message=(
                "No ready task is available to start. Remaining tasks are draft-only and must "
                "be promoted to ready first."
            ),
        )

    monkeypatch.setattr("engram.mcp.tools.start_workflow", raising_start_draft_only)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    start_handler = server.tools["engram_workflow_start"]

    res_start_blocked = asyncio.run(start_handler())
    assert "# Start Blocked" in res_start_blocked
    assert "Reason: No ready task is available to start." in res_start_blocked
    assert "## Next action" in res_start_blocked
    assert res_start_blocked.count("## Next action") == 1
    assert "set status=ready via engram_task_update" in res_start_blocked
    assert "ok:" not in res_start_blocked.lower()
    assert "error:" not in res_start_blocked.lower()


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
        "PROJECT_NOT_BOUND",
        "UNRESOLVED_WORKSPACE",
    ]

    for code in known_codes:
        exc = EngramServiceError(code=code, message=f"Test error {code}")
        res = yaml.safe_load(_respond_error(exc))
        assert res["ok"] is False
        assert res["error"] == code
        assert res["message"] == f"Test error {code}"
        assert "fix" in res
        if code != "UNRESOLVED_WORKSPACE":
            assert "engram_" in res["fix"]  # references MCP tool names

    # Unknown/unexpected error should not have fix field
    exc_unknown = EngramServiceError(code="SOME_UNKNOWN_ERROR", message="An unknown error")
    res_unknown = yaml.safe_load(_respond_error(exc_unknown))
    assert res_unknown["ok"] is False
    assert res_unknown["error"] == "SOME_UNKNOWN_ERROR"
    assert "fix" not in res_unknown


def test_mcp_error_response_ready_metadata_includes_compact_actionable_details() -> None:
    """Verify READY_METADATA_INCOMPLETE includes compact details and field-specific remediation."""
    from engram.mcp.tools import _respond_error
    from engram.services.errors import EngramServiceError

    exc = EngramServiceError(
        code="READY_METADATA_INCOMPLETE",
        message="Task cannot be promoted to ready until required metadata is complete and sufficiently specific.",
        details={
            "status": "ready",
            "evaluated_fields": ["description", "acceptance", "relevant_files"],
            "missing_fields": ["description"],
            "weak_fields": ["acceptance", "relevant_files"],
            "weak_field_reasons": {
                "acceptance": "Acceptance criteria are too generic.",
                "relevant_files": "Relevant files are too broad.",
            },
            "required_fields": ["description", "acceptance", "relevant_files"],
        },
    )

    res = yaml.safe_load(_respond_error(exc))
    assert res["ok"] is False
    assert res["error"] == "READY_METADATA_INCOMPLETE"
    assert set(res["details"].keys()) == {
        "evaluated_fields",
        "missing_fields",
        "weak_fields",
        "weak_field_reasons",
    }
    assert res["details"]["missing_fields"] == ["description"]
    assert res["details"]["weak_fields"] == ["acceptance", "relevant_files"]
    assert "Retry engram_task_update with status=ready" in res["fix"]
    assert "Missing: description." in res["fix"]
    assert "Strengthen: acceptance, relevant_files." in res["fix"]
    assert "Weak-field reasons: acceptance (Acceptance criteria are too generic.)" in res["fix"]


def test_mcp_phase_create_happy_and_error_paths(tmp_db, monkeypatch) -> None:
    """Verify engram_phase_create tool creates a phase and gracefully handles validation errors."""
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

    create_handler = server.tools["engram_phase_create"]

    # 1. Happy path
    res = yaml.safe_load(
        create_handler(
            title="MCP Phase 1",
            description="Testing phase creation over MCP",
            status="planned",
            acceptance="Must be green",
        )
    )
    assert res["ok"] is True
    assert "id" in res
    assert res["title"] == "MCP Phase 1"

    # Verify actual persistence
    from engram.models.phase import Phase

    phase = Phase.get(res["id"])
    assert phase is not None
    assert phase.title == "MCP Phase 1"
    assert phase.description == "Testing phase creation over MCP"

    # 2. Validation error path (duplicate title)
    res_err = yaml.safe_load(
        create_handler(
            title="MCP Phase 1",
        )
    )
    assert res_err["ok"] is False
    assert res_err["error"] == "DUPLICATE_PHASE_TITLE"

    # 3. Validation error path (invalid status)
    res_err2 = yaml.safe_load(
        create_handler(
            title="MCP Phase 2",
            status="invalid-status",
        )
    )
    assert res_err2["ok"] is False
    assert res_err2["error"] == "INVALID_PHASE_STATUS"


def test_mcp_project_init_success(tmp_path, monkeypatch) -> None:
    """Verify engram_project_init creates project, db, and gitignore."""
    repo_path = tmp_path / "repo_mcp_init"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    monkeypatch.setattr("os.getcwd", lambda: str(repo_path))

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    init_handler = server.tools["engram_project_init"]

    res = yaml.safe_load(
        init_handler(
            name="MCP Bound Project",
            project_id="mcp-bound-proj",
            summary="MCP summary description",
        )
    )

    assert res["ok"] is True
    assert res["created"] is True
    assert res["project"]["id"] == "mcp-bound-proj"
    assert res["project"]["name"] == "MCP Bound Project"
    assert "hint" in res

    # Verify DB file is created
    db_path = repo_path / ".engram" / "memory.db"
    assert db_path.exists()

    # Verify .gitignore is created and contains .engram/
    gitignore_path = repo_path / ".gitignore"
    assert gitignore_path.exists()
    assert ".engram/" in gitignore_path.read_text(encoding="utf-8")


def test_mcp_project_init_unbound_raises_unresolved_workspace(tmp_path, monkeypatch) -> None:
    """Verify engram_project_init returns UNRESOLVED_WORKSPACE when run outside git repository."""
    unbound_path = tmp_path / "unbound_dir"
    unbound_path.mkdir()

    monkeypatch.setattr("os.getcwd", lambda: str(unbound_path))

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    init_handler = server.tools["engram_project_init"]

    res = yaml.safe_load(init_handler())
    assert res["ok"] is False
    assert res["error"] == "UNRESOLVED_WORKSPACE"
    assert "git init" in res["fix"]


def test_mcp_project_init_and_diagnostics_work_across_fresh_workspaces_with_same_handlers(
    tmp_path, monkeypatch
) -> None:
    """Verify MCP init/status/diagnostics are workspace-based across fresh repos."""
    repo_a = tmp_path / "repo_a"
    repo_b = tmp_path / "repo_b"
    repo_a.mkdir()
    repo_b.mkdir()
    (repo_a / ".git").mkdir()
    (repo_b / ".git").mkdir()

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    current_handler = server.tools["engram_project_current"]
    init_handler = server.tools["engram_project_init"]
    diagnostics_handler = server.tools["engram_project_diagnostics"]

    # Guard against accidental CLI dependency in normal MCP init/status flow.
    def _raise_if_cli_used(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("CLI command path should not be called by MCP init/status tools.")

    monkeypatch.setattr("engram.cli.project_cmds.init", _raise_if_cli_used)

    for repo_path, project_id in ((repo_a, "mcp-proj-a"), (repo_b, "mcp-proj-b")):
        monkeypatch.setattr("os.getcwd", lambda p=repo_path: str(p))

        before = yaml.safe_load(current_handler())
        assert before["ok"] is True
        assert before["initialized"] is False
        assert before["status"] in {"uninitialized", "unresolved-workspace"}
        assert "next" in before

        initialized = yaml.safe_load(
            init_handler(
                name=f"Project {project_id}",
                project_id=project_id,
                summary=f"Summary {project_id}",
            )
        )
        assert initialized["ok"] is True
        assert initialized["project"]["id"] == project_id

        current = yaml.safe_load(current_handler())
        assert current["ok"] is True
        assert current["initialized"] is True
        assert current["status"] == "ready"
        assert current["project"]["id"] == project_id
        assert current["repo_root"] == str(repo_path)

        diagnostics = yaml.safe_load(diagnostics_handler())
        assert diagnostics["ok"] is True
        assert diagnostics["status"] == "healthy"
        assert diagnostics["repo_root"] == str(repo_path)
        assert diagnostics["repo_root_detected"] is True
        assert diagnostics["db"]["exists"] is True
        assert diagnostics["db"]["schema_ok"] is True
        assert diagnostics["gitignore"]["status"] == "configured"


def test_mcp_diagnostics_repo_local_states(tmp_path, monkeypatch) -> None:
    """Verify engram_project_current and engram_project_diagnostics produce stable, actionable states across fresh workspaces."""
    import yaml

    from engram.mcp.tools import register_tools

    # 1. unresolved-workspace state (directory is NOT in a git repo)
    unresolved_dir = tmp_path / "unresolved_dir"
    unresolved_dir.mkdir()
    monkeypatch.setattr("os.getcwd", lambda: str(unresolved_dir))

    server = MockServer()
    register_tools(server)
    current_handler = server.tools["engram_project_current"]
    diagnostics_handler = server.tools["engram_project_diagnostics"]

    # In unresolved-workspace:
    cur_unresolved = yaml.safe_load(current_handler())
    assert cur_unresolved["ok"] is True
    assert cur_unresolved["initialized"] is False
    assert cur_unresolved["status"] == "unresolved-workspace"
    assert "git init" in cur_unresolved["next"]

    diag_unresolved = yaml.safe_load(diagnostics_handler())
    assert diag_unresolved["ok"] is True
    assert diag_unresolved["status"] == "unresolved-workspace"
    assert diag_unresolved["repo_root_detected"] is False
    assert "git init" in diag_unresolved["next_action"]

    # 2. uninitialized state (directory IS a git repo but has no .engram dir/db)
    repo_dir = tmp_path / "fresh_repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    monkeypatch.setattr("os.getcwd", lambda: str(repo_dir))

    # In uninitialized repository:
    cur_uninit = yaml.safe_load(current_handler())
    assert cur_uninit["ok"] is True
    assert cur_uninit["initialized"] is False
    assert cur_uninit["status"] == "uninitialized"
    assert "engram_project_init" in cur_uninit["next"]

    diag_uninit = yaml.safe_load(diagnostics_handler())
    assert diag_uninit["ok"] is True
    assert diag_uninit["status"] == "uninitialized"
    assert diag_uninit["repo_root_detected"] is True
    assert "engram_project_init" in diag_uninit["next_action"]
