"""Tests for MCP adapter package boundaries and startup bootstrap."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
from typing import Any

MCP_MODULES = (
    "engram.mcp",
    "engram.mcp.server",
    "engram.mcp.tools",
    "engram.mcp.resources",
    "engram.mcp.schemas",
)
MCP_FILES = ("__init__.py", "server.py", "tools.py", "resources.py", "schemas.py")
BANNED_IMPORT_PREFIXES = ("click", "rich", "engram.cli", "engram.commands", "subprocess")


def test_mcp_package_skeleton_files_exist():
    package_dir = Path(importlib.import_module("engram").__file__).resolve().parent / "mcp"
    for filename in MCP_FILES:
        assert (package_dir / filename).is_file()


def test_mcp_modules_do_not_import_cli_or_shell_dependencies():
    for module_name in MCP_MODULES:
        module = importlib.import_module(module_name)
        source = Path(module.__file__).read_text(encoding="utf-8")
        parsed = ast.parse(source)
        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(BANNED_IMPORT_PREFIXES)
            elif isinstance(node, ast.ImportFrom):
                imported_module = node.module or ""
                assert not imported_module.startswith(BANNED_IMPORT_PREFIXES)


def test_run_stdio_server_initializes_db_once_and_uses_stdio_transport(monkeypatch):
    module = importlib.import_module("engram.mcp.server")
    events: list[tuple[str, str | None]] = []

    class _FakeFastMCP:
        def __init__(self, name: str):
            self.name = name
            events.append(("create_server", name))

        def run(self, *, transport: str) -> None:
            events.append(("run", transport))

    monkeypatch.setattr(module, "init_db", lambda: events.append(("init_db", None)))
    monkeypatch.setattr(
        module,
        "register_resources",
        lambda server: events.append(("register_resources", getattr(server, "name", None))),
    )
    monkeypatch.setattr(
        module,
        "register_tools",
        lambda server: events.append(("register_tools", getattr(server, "name", None))),
    )
    monkeypatch.setattr(module, "_load_fastmcp_class", lambda: _FakeFastMCP)

    module.run_stdio_server()

    assert events == [
        ("init_db", None),
        ("create_server", "engram"),
        ("register_resources", "engram"),
        ("register_tools", "engram"),
        ("run", "stdio"),
    ]


def test_load_fastmcp_class_missing_dependency_has_clear_install_message(monkeypatch):
    module = importlib.import_module("engram.mcp.server")

    def _raise_module_not_found(_name: str) -> object:
        raise ModuleNotFoundError("No module named 'mcp'", name="mcp")

    monkeypatch.setattr(module, "import_module", _raise_module_not_found)

    try:
        module._load_fastmcp_class()
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected RuntimeError when MCP SDK is missing.")

    assert "Missing optional MCP dependency" in message
    assert "engram[mcp]" in message


def test_register_resources_registers_expected_fastmcp_resources(monkeypatch) -> None:
    """Verify that register_resources registers the four expected URIs and returns strings."""

    class MockServer:
        """A mock implementation of the FastMCP server for registration testing."""

        def __init__(self) -> None:
            self.resources: dict[str, Any] = {}

        def resource(self, uri: str, **kwargs: Any) -> Any:
            """Mock the resource decorator."""

            def decorator(func: Any) -> Any:
                self.resources[uri] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.resources import register_resources

    # Mock the context services to return stable dummy strings for simple registration check
    monkeypatch.setattr(
        "engram.mcp.resources.get_startup_context_for_current_project",
        lambda: "startup_payload",
    )
    monkeypatch.setattr(
        "engram.mcp.resources.get_snapshot_context_for_current_project",
        lambda: "snapshot_payload",
    )
    monkeypatch.setattr(
        "engram.mcp.resources.get_handoff_context_for_current_project",
        lambda: "handoff_payload",
    )

    register_resources(server)

    assert "engram://startup" in server.resources
    assert "engram://task/{task_id}/context" in server.resources
    assert "engram://snapshot" in server.resources
    assert "engram://handoff" in server.resources

    # Verify resource returns
    assert server.resources["engram://startup"]() == "startup_payload"
    assert (
        server.resources["engram://task/{task_id}/context"]("test-task") == "placeholder: test-task"
    )
    assert server.resources["engram://snapshot"]() == "snapshot_payload"
    assert server.resources["engram://handoff"]() == "handoff_payload"


def test_mcp_resources_wire_to_context_service_and_resolve_bound_project(tmp_db, monkeypatch):
    """Verify resources correctly resolve the bound project and invoke context service builders."""
    import os

    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-bound-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-mcp-1",
        name="MCP Project",
        summary="Test project for MCP",
        repo_paths=[cwd],
    )

    # Mock context builders to verify they receive project ID
    monkeypatch.setattr(
        "engram.services.context_service.context.get_startup_context",
        lambda pid: f"startup:{pid}",
    )
    monkeypatch.setattr(
        "engram.services.context_service.context.get_snapshot_context",
        lambda pid: f"snapshot:{pid}",
    )
    monkeypatch.setattr(
        "engram.services.context_service.context.get_handoff_context",
        lambda pid: f"handoff:{pid}",
    )

    class MockServer:
        def __init__(self):
            self.resources = {}

        def resource(self, uri, **kwargs):
            def decorator(func):
                self.resources[uri] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.resources import register_resources

    register_resources(server)

    assert server.resources["engram://startup"]() == "startup:proj-mcp-1"
    assert server.resources["engram://snapshot"]() == "snapshot:proj-mcp-1"
    assert server.resources["engram://handoff"]() == "handoff:proj-mcp-1"


def test_mcp_resources_raise_project_not_bound_for_unbound_repos(tmp_db, monkeypatch):
    """Verify that calling resources when the working directory is unbound raises EngramServiceError."""
    import os

    import pytest

    from engram.services.errors import EngramServiceError

    cwd = os.path.abspath("repo/fake-unbound-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    class MockServer:
        def __init__(self):
            self.resources = {}

        def resource(self, uri, **kwargs):
            def decorator(func):
                self.resources[uri] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.resources import register_resources

    register_resources(server)

    for uri in ["engram://startup", "engram://snapshot", "engram://handoff"]:
        with pytest.raises(EngramServiceError) as raised:
            server.resources[uri]()
        assert raised.value.code == "PROJECT_NOT_BOUND"


def test_mcp_resources_are_read_only_and_do_not_mutate_db(tmp_db, monkeypatch):
    """Verify that resource invocations do not mutate project, task, phase, or memory rows."""
    import os

    from engram.db import get_db_connection
    from engram.models.memory import Memory
    from engram.models.phase import Phase
    from engram.models.project import Project
    from engram.models.task import Task

    def _table_rows(table_name: str) -> list[dict[str, object]]:
        conn = get_db_connection()
        rows = conn.execute(f"SELECT * FROM {table_name} ORDER BY rowid ASC").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    cwd = os.path.abspath("repo/fake-read-only-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-ro",
        name="MCP Project RO",
        summary="Test project for MCP RO",
        repo_paths=[cwd],
    )
    phase = Phase.create(
        project_id=project.id, id="phase1001", title="Active phase", status="active"
    )
    Task.create(
        project_id=project.id,
        id="task1001",
        title="RO Task",
        phase=phase.title,
        phase_id=phase.id,
    )
    Memory.create(
        project_id=project.id,
        id="memo1001",
        type="note",
        title="RO Memory",
        content="Testing read only.",
        tags=["mcp"],
        level="L3",
    )

    before_rows = {
        "projects": _table_rows("projects"),
        "tasks": _table_rows("tasks"),
        "phases": _table_rows("phases"),
        "memories": _table_rows("memories"),
    }

    # Mock context services to return safe values
    monkeypatch.setattr(
        "engram.services.context_service.context.get_startup_context",
        lambda pid: f"startup:{pid}",
    )
    monkeypatch.setattr(
        "engram.services.context_service.context.get_snapshot_context",
        lambda pid: f"snapshot:{pid}",
    )
    monkeypatch.setattr(
        "engram.services.context_service.context.get_handoff_context",
        lambda pid: f"handoff:{pid}",
    )

    class MockServer:
        def __init__(self):
            self.resources = {}

        def resource(self, uri, **kwargs):
            def decorator(func):
                self.resources[uri] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.resources import register_resources

    register_resources(server)

    server.resources["engram://startup"]()
    server.resources["engram://snapshot"]()
    server.resources["engram://handoff"]()

    after_rows = {
        "projects": _table_rows("projects"),
        "tasks": _table_rows("tasks"),
        "phases": _table_rows("phases"),
        "memories": _table_rows("memories"),
    }

    assert after_rows == before_rows
