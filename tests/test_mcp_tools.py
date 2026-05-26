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
    """Verify that register_tools registers the engram_project_current tool."""
    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    assert "engram_project_current" in server.tools
    assert server.tools["engram_project_current"].__name__ == "engram_project_current"


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

    after_rows = {
        "projects": _table_rows("projects"),
        "tasks": _table_rows("tasks"),
        "phases": _table_rows("phases"),
        "memories": _table_rows("memories"),
    }

    assert after_rows == before_rows
