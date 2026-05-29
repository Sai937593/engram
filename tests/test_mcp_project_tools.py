"""Tests for MCP project registration, init, and switch tools."""

from __future__ import annotations

import pytest
import yaml

from engram.models.project import Project
from engram.services.project_service import get_active_project_id, switch_project


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


@pytest.fixture(autouse=True)
def setup_active_file(tmp_path, monkeypatch):
    """Isolate active project configuration file for each test."""
    active_file = tmp_path / "active_project"
    monkeypatch.setattr("engram.services.project_service.ACTIVE_PROJECT_FILE", active_file)
    return active_file


def test_register_project_tools_registers_init_and_switch() -> None:
    """Verify that engram_project_init and engram_project_switch are registered."""
    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    assert "engram_project_init" in server.tools
    assert "engram_project_switch" in server.tools


def test_mcp_project_init_success(tmp_db, tmp_path) -> None:
    """Verify engram_project_init tool creates project and sets active."""
    repo_dir = tmp_path / "init-repo"
    repo_dir.mkdir()

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    init_handler = server.tools["engram_project_init"]

    res = yaml.safe_load(
        init_handler(
            id="proj-init-mcp",
            name="MCP Init Project",
            summary="MCP Init Summary",
            repo_path=str(repo_dir),
        )
    )

    assert res["ok"] is True
    assert res["id"] == "proj-init-mcp"
    assert res["name"] == "MCP Init Project"

    # Verify active project was set
    assert get_active_project_id() == "proj-init-mcp"


def test_mcp_project_switch_success(tmp_db) -> None:
    """Verify engram_project_switch tool switches the active project."""
    Project.create(id="projA", name="Project A")
    Project.create(id="projB", name="Project B")

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    switch_handler = server.tools["engram_project_switch"]

    res = yaml.safe_load(switch_handler(project_id="projB"))
    assert res["ok"] is True
    assert res["id"] == "projB"
    assert res["name"] == "Project B"

    # Verify active project was set
    assert get_active_project_id() == "projB"


def test_mcp_project_resolution_with_no_active_project_raised_or_single_auto(tmp_db) -> None:
    """Verify active project resolution logic in MCP tools (raises or auto-selects)."""
    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    current_handler = server.tools["engram_project_current"]

    # 1. Multiple projects in DB, no active set -> raises PROJECT_NOT_BOUND
    Project.create(id="proj1", name="Project 1")
    Project.create(id="proj2", name="Project 2")

    res = yaml.safe_load(current_handler())
    assert res["ok"] is False
    assert res["error"] == "PROJECT_NOT_BOUND"

    # 2. Switch to one -> resolves successfully
    switch_project("proj1")
    res2 = yaml.safe_load(current_handler())
    assert res2["ok"] is True
    assert res2["project"]["id"] == "proj1"
