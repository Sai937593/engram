"""Tests for engram project init and switch MCP tools."""

from __future__ import annotations

from typing import Any

import pytest
import yaml


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


@pytest.fixture
def temp_active_file(tmp_path, monkeypatch):
    tmp_file = tmp_path / "active_project"
    monkeypatch.setattr("engram.services.project_service.ACTIVE_PROJECT_FILE_PATH", tmp_file)
    return tmp_file


def test_mcp_project_tools_registration(temp_active_file) -> None:
    """Verify that project init and switch tools are registered correctly."""
    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    assert "engram_project_init" in server.tools
    assert "engram_project_switch" in server.tools


def test_mcp_project_init_and_switch_and_current_flow(tmp_db, temp_active_file) -> None:
    """Verify the project init, switch, and current tool sequence."""
    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    init_handler = server.tools["engram_project_init"]
    switch_handler = server.tools["engram_project_switch"]
    current_handler = server.tools["engram_project_current"]

    # 1. Calling current first raises NO_ACTIVE_PROJECT since no active project is set
    res_current_err = yaml.safe_load(current_handler())
    assert res_current_err["ok"] is False
    assert res_current_err["error"] == "NO_ACTIVE_PROJECT"

    # 2. Call init tool to initialize 'mcp-proj-1'
    res_init = yaml.safe_load(
        init_handler(
            id="mcp-proj-1",
            name="MCP Project 1",
            summary="MCP test project 1",
            repo_paths=["/path/repo-1"],
        )
    )
    assert res_init["ok"] is True
    assert res_init["project"]["id"] == "mcp-proj-1"
    assert res_init["project"]["name"] == "MCP Project 1"

    # 3. Call current tool; it should now successfully return 'mcp-proj-1'
    res_current = yaml.safe_load(current_handler())
    assert res_current["ok"] is True
    assert res_current["project"]["id"] == "mcp-proj-1"
    assert res_current["project"]["name"] == "MCP Project 1"

    # 4. Initialize another project 'mcp-proj-2'
    res_init_2 = yaml.safe_load(
        init_handler(
            id="mcp-proj-2",
            name="MCP Project 2",
        )
    )
    assert res_init_2["ok"] is True
    assert res_init_2["project"]["id"] == "mcp-proj-2"

    # 5. Call current tool; it should return 'mcp-proj-2' since init sets it active
    res_current_2 = yaml.safe_load(current_handler())
    assert res_current_2["ok"] is True
    assert res_current_2["project"]["id"] == "mcp-proj-2"

    # 6. Switch back to 'mcp-proj-1' using switch tool
    res_switch = yaml.safe_load(switch_handler(id="mcp-proj-1"))
    assert res_switch["ok"] is True
    assert res_switch["project"]["id"] == "mcp-proj-1"

    # 7. Call current tool; it should return 'mcp-proj-1' again
    res_current_3 = yaml.safe_load(current_handler())
    assert res_current_3["ok"] is True
    assert res_current_3["project"]["id"] == "mcp-proj-1"
