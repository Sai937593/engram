"""Consolidated startup reliability and packaging stability tests for the Engram MCP adapter."""

from __future__ import annotations

import asyncio
import sys
from importlib.metadata import distribution, entry_points
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from engram.services.errors import EngramServiceError


class MockServer:
    """Mock implementation of a FastMCP server to inspect registered tools/resources."""

    def __init__(self) -> None:
        self.name = "engram"
        self.tools: dict[str, Any] = {}
        self.resources: dict[str, Any] = {}
        self.run_called = False
        self.run_transport = None

    def tool(self, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.tools[func.__name__] = func
            return func

        return decorator

    def resource(self, uri: str, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.resources[uri] = func
            return func

        return decorator

    def run(self, *, transport: str) -> None:
        self.run_called = True
        self.run_transport = transport


@pytest.fixture
def unresolved_workspace(tmp_path, monkeypatch):
    """Fixture providing a directory that is not inside any Git repository."""
    workspace_dir = tmp_path / "unresolved_workspace"
    workspace_dir.mkdir()
    monkeypatch.setattr("os.getcwd", lambda: str(workspace_dir))
    return workspace_dir


@pytest.fixture
def uninitialized_workspace(tmp_path, monkeypatch):
    """Fixture providing a Git repository that has not been initialized with Engram."""
    workspace_dir = tmp_path / "uninitialized_workspace"
    workspace_dir.mkdir()
    (workspace_dir / ".git").mkdir()
    monkeypatch.setattr("os.getcwd", lambda: str(workspace_dir))
    return workspace_dir


@pytest.fixture
def initialized_workspace(tmp_path, monkeypatch):
    """Fixture providing a Git repository fully initialized with Engram project state."""
    workspace_dir = tmp_path / "initialized_workspace"
    workspace_dir.mkdir()
    (workspace_dir / ".git").mkdir()
    monkeypatch.setattr("os.getcwd", lambda: str(workspace_dir))

    from engram.services.project_service import initialize_project

    initialize_project(
        cwd=str(workspace_dir),
        name="Reliability Project",
        project_id="reliability-proj",
        summary="Testing project startup reliability",
    )
    return workspace_dir


def test_mcp_server_bootstrap_unresolved_workspace(unresolved_workspace, monkeypatch):
    """Verify that MCP server bootstrap completes without exception in an unresolved workspace."""
    import engram.mcp.server as mcp_server

    mock_server = MockServer()
    monkeypatch.setattr(mcp_server, "create_server", lambda: mock_server)

    # Track if init_db is called
    init_db_called = False

    def dummy_init_db():
        nonlocal init_db_called
        init_db_called = True

    monkeypatch.setattr(mcp_server, "init_db", dummy_init_db)

    # run_stdio_server should execute without exceptions
    mcp_server.run_stdio_server()

    # DB init should not run since no local DB exists/is bound
    assert init_db_called is False
    assert mock_server.run_called is True
    assert mock_server.run_transport == "stdio"

    # All tools and resources registered
    assert len(mock_server.tools) > 0
    assert len(mock_server.resources) > 0


def test_mcp_server_bootstrap_uninitialized_workspace(uninitialized_workspace, monkeypatch):
    """Verify that MCP server bootstrap completes without exception in an uninitialized workspace."""
    import engram.mcp.server as mcp_server

    mock_server = MockServer()
    monkeypatch.setattr(mcp_server, "create_server", lambda: mock_server)

    init_db_called = False

    def dummy_init_db():
        nonlocal init_db_called
        init_db_called = True

    monkeypatch.setattr(mcp_server, "init_db", dummy_init_db)

    mcp_server.run_stdio_server()

    # DB init should not run since no local DB exists/is bound
    assert init_db_called is False
    assert mock_server.run_called is True
    assert mock_server.run_transport == "stdio"


def test_mcp_server_bootstrap_initialized_workspace(initialized_workspace, monkeypatch):
    """Verify that MCP server bootstrap completes and initializes the DB in an initialized workspace."""
    import engram.mcp.server as mcp_server

    mock_server = MockServer()
    monkeypatch.setattr(mcp_server, "create_server", lambda: mock_server)

    init_db_called = False

    def dummy_init_db():
        nonlocal init_db_called
        init_db_called = True

    monkeypatch.setattr(mcp_server, "init_db", dummy_init_db)

    mcp_server.run_stdio_server()

    # DB init must run since local DB is configured and exists
    assert init_db_called is True
    assert mock_server.run_called is True


def test_mcp_server_main_cli_missing_optional_dependency(monkeypatch):
    """Verify that main() exits cleanly with an error message if the MCP dependency is missing."""
    import engram.mcp.server as mcp_server

    def mock_load_fastmcp():
        raise RuntimeError(
            'Missing optional MCP dependency. Install it with: uv pip install "engram[mcp]"'
        )

    monkeypatch.setattr(mcp_server, "_load_fastmcp_class", mock_load_fastmcp)

    stderr_writes = []
    monkeypatch.setattr(sys.stderr, "write", lambda s: stderr_writes.append(s))

    exit_codes = []

    def mock_exit(code):
        exit_codes.append(code)
        raise SystemExit(code)

    monkeypatch.setattr(sys, "exit", mock_exit)

    with pytest.raises(SystemExit) as sysexit_info:
        mcp_server.main()

    assert sysexit_info.value.code == 1
    assert len(exit_codes) == 1
    assert exit_codes[0] == 1
    assert any("Missing optional MCP dependency" in chunk for chunk in stderr_writes)


def test_mcp_tools_graceful_degradation_unresolved_workspace(unresolved_workspace):
    """Verify all 17 registered MCP tools degrade gracefully in an unresolved workspace."""
    mock_server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(mock_server)

    # Map each tool to arguments that satisfy signature requirements
    tool_inputs = {
        "engram_project_current": {},
        "engram_project_diagnostics": {},
        "engram_workflow_start": {},
        "engram_workflow_finish": {"commit_type": "feat"},
        "engram_task_list": {},
        "engram_task_get": {"task_ref": "task-1"},
        "engram_task_next": {},
        "engram_task_create": {"title": "T1"},
        "engram_task_update": {"task_ref": "task-1", "updates": {}},
        "engram_task_note_append": {"task_ref": "task-1", "note": "N"},
        "engram_task_start": {"task_ref": "task-1"},
        "engram_task_done": {"task_ref": "task-1"},
        "engram_memory_create": {"type": "lesson", "title": "T", "content": "C"},
        "engram_memory_search": {},
        "engram_phase_list": {},
        "engram_phase_create": {"title": "P1"},
        "engram_phase_start": {"phase_ref": "P1"},
        "engram_phase_complete": {"phase_ref": "P1"},
    }

    # Patch sys.modules to remove "pytest" so project_service behaves as in production
    with patch.dict(sys.modules):
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        for tool_name, tool_func in mock_server.tools.items():
            if tool_name == "engram_project_init":
                continue

            kwargs = tool_inputs.get(tool_name, {})

            # Invoke sync or async tool handler
            if asyncio.iscoroutinefunction(tool_func):
                res_str = asyncio.run(tool_func(**kwargs))
            else:
                res_str = tool_func(**kwargs)

            # Response must be a valid serialized YAML string
            res = yaml.safe_load(res_str)

            if tool_name in ("engram_project_current", "engram_project_diagnostics"):
                assert res["ok"] is True
                assert res["status"] == "unresolved-workspace"
                assert "git init" in (res.get("next") or res.get("next_action") or "")
            else:
                assert res["ok"] is False
                assert res["error"] in ("UNRESOLVED_WORKSPACE", "PROJECT_NOT_BOUND")
                assert "fix" in res


def test_mcp_tools_graceful_degradation_uninitialized_workspace(uninitialized_workspace):
    """Verify registered MCP tools degrade gracefully in an uninitialized workspace."""
    mock_server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(mock_server)

    tool_inputs = {
        "engram_project_current": {},
        "engram_project_diagnostics": {},
        "engram_workflow_start": {},
        "engram_workflow_finish": {"commit_type": "feat"},
        "engram_task_list": {},
        "engram_task_get": {"task_ref": "task-1"},
        "engram_task_next": {},
        "engram_task_create": {"title": "T1"},
        "engram_task_update": {"task_ref": "task-1", "updates": {}},
        "engram_task_note_append": {"task_ref": "task-1", "note": "N"},
        "engram_task_start": {"task_ref": "task-1"},
        "engram_task_done": {"task_ref": "task-1"},
        "engram_memory_create": {"type": "lesson", "title": "T", "content": "C"},
        "engram_memory_search": {},
        "engram_phase_list": {},
        "engram_phase_create": {"title": "P1"},
        "engram_phase_start": {"phase_ref": "P1"},
        "engram_phase_complete": {"phase_ref": "P1"},
    }

    # Patch sys.modules to remove "pytest" so project_service behaves as in production
    with patch.dict(sys.modules):
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        for tool_name, tool_func in mock_server.tools.items():
            if tool_name == "engram_project_init":
                continue

            kwargs = tool_inputs.get(tool_name, {})

            if asyncio.iscoroutinefunction(tool_func):
                res_str = asyncio.run(tool_func(**kwargs))
            else:
                res_str = tool_func(**kwargs)

            res = yaml.safe_load(res_str)

            if tool_name in ("engram_project_current", "engram_project_diagnostics"):
                assert res["ok"] is True
                assert res["status"] == "uninitialized"
                assert "engram_project_init" in (res.get("next") or res.get("next_action") or "")
            else:
                assert res["ok"] is False
                assert res["error"] == "PROJECT_NOT_BOUND"
                assert "fix" in res


def test_mcp_project_init_tool_unresolved_workspace(unresolved_workspace):
    """Verify that engram_project_init degrades cleanly in an unresolved workspace."""
    mock_server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(mock_server)

    init_handler = mock_server.tools["engram_project_init"]

    with patch.dict(sys.modules):
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        res = yaml.safe_load(init_handler(name="Test"))
        assert res["ok"] is False
        assert res["error"] == "UNRESOLVED_WORKSPACE"
        assert "git init" in res["fix"]


def test_mcp_project_init_tool_uninitialized_workspace(uninitialized_workspace):
    """Verify that engram_project_init initializes the workspace cleanly."""
    mock_server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(mock_server)

    init_handler = mock_server.tools["engram_project_init"]

    with patch.dict(sys.modules):
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        res = yaml.safe_load(init_handler(name="Test Project"))
        assert res["ok"] is True
        assert res["created"] is True
        assert res["project"]["name"] == "Test Project"
        assert (uninitialized_workspace / ".engram" / "memory.db").exists()


def test_mcp_resources_graceful_degradation_unresolved_workspace(unresolved_workspace):
    """Verify all 4 registered MCP resources raise PROJECT_NOT_BOUND/UNRESOLVED_WORKSPACE in unresolved workspace."""
    mock_server = MockServer()
    from engram.mcp.resources import register_resources

    register_resources(mock_server)

    assert len(mock_server.resources) == 4

    # Patch sys.modules to remove "pytest" so project_service behaves as in production
    with patch.dict(sys.modules):
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        for uri, resource_func in mock_server.resources.items():
            with pytest.raises(EngramServiceError) as exc_info:
                if uri == "engram://task/{task_id}/context":
                    resource_func("task-1")
                else:
                    resource_func()

            assert exc_info.value.code in ("UNRESOLVED_WORKSPACE", "PROJECT_NOT_BOUND")


def test_mcp_resources_graceful_degradation_uninitialized_workspace(uninitialized_workspace):
    """Verify all 4 registered MCP resources raise PROJECT_NOT_BOUND in uninitialized workspace."""
    mock_server = MockServer()
    from engram.mcp.resources import register_resources

    register_resources(mock_server)

    # Patch sys.modules to remove "pytest" so project_service behaves as in production
    with patch.dict(sys.modules):
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        for uri, resource_func in mock_server.resources.items():
            with pytest.raises(EngramServiceError) as exc_info:
                if uri == "engram://task/{task_id}/context":
                    resource_func("task-1")
                else:
                    resource_func()

            assert exc_info.value.code == "PROJECT_NOT_BOUND"


def test_packaging_metadata_stability():
    """Verify console entrypoints and optional extras are declared and well-formed."""
    scripts = entry_points(group="console_scripts")

    # engram companion CLI script
    cli_script = next((ep for ep in scripts if ep.name == "engram"), None)
    assert cli_script is not None
    assert cli_script.value == "engram.cli:main"

    # engram-mcp server script
    mcp_script = next((ep for ep in scripts if ep.name == "engram-mcp"), None)
    assert mcp_script is not None
    assert mcp_script.value == "engram.mcp.server:main"

    # mcp extra dependency checks
    dist_reqs = distribution("engram").requires or []
    assert any(req.startswith("mcp") and 'extra == "mcp"' in req for req in dist_reqs)
