"""Tests for MCP adapter package boundaries and startup bootstrap."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml

MCP_MODULES = (
    "engram.mcp",
    "engram.mcp.server",
    "engram.mcp.tools",
    "engram.mcp.tools.helpers",
    "engram.mcp.tools.task_tools",
    "engram.mcp.tools.memory_tools",
    "engram.mcp.tools.phase_tools",
    "engram.mcp.tools.workflow_tools",
    "engram.mcp.resources",
    "engram.mcp.schemas",
)
MCP_FILES = ("__init__.py", "server.py", "resources.py", "schemas.py")
BANNED_IMPORT_PREFIXES = ("click", "rich", "engram.cli", "engram.commands", "subprocess")


def test_mcp_package_skeleton_files_exist():
    package_dir = Path(importlib.import_module("engram").__file__).resolve().parent / "mcp"
    for filename in MCP_FILES:
        assert (package_dir / filename).is_file()
    assert (package_dir / "tools" / "__init__.py").is_file()


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
        "engram.mcp.resources.get_startup_context_for_active_project",
        lambda: "startup_payload",
    )
    monkeypatch.setattr(
        "engram.mcp.resources.get_snapshot_context_for_active_project",
        lambda: "snapshot_payload",
    )
    monkeypatch.setattr(
        "engram.mcp.resources.get_handoff_context_for_active_project",
        lambda: "handoff_payload",
    )
    monkeypatch.setattr(
        "engram.mcp.resources.get_task_context_for_active_project",
        lambda task_id: f"task_payload:{task_id}",
    )

    register_resources(server)

    assert "engram://startup" in server.resources
    assert "engram://task/{task_id}/context" in server.resources
    assert "engram://snapshot" in server.resources
    assert "engram://handoff" in server.resources

    # Verify resource returns
    assert server.resources["engram://startup"]() == "startup_payload"
    assert (
        server.resources["engram://task/{task_id}/context"]("test-task") == "task_payload:test-task"
    )
    assert server.resources["engram://snapshot"]() == "snapshot_payload"
    assert server.resources["engram://handoff"]() == "handoff_payload"


def test_mcp_resources_wire_to_context_service_and_resolve_bound_project(tmp_db, monkeypatch):
    """Verify resources correctly resolve the bound project and invoke context service builders."""
    import os

    import pytest

    from engram.models.phase import Phase
    from engram.models.project import Project
    from engram.models.task import Task
    from engram.services.errors import EngramServiceError

    cwd = os.path.abspath("repo/fake-bound-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-1",
        name="MCP Project",
        summary="Test project for MCP",
        repo_paths=[cwd],
    )
    phase = Phase.create(
        project_id=project.id,
        id="phase-1",
        title="Test Phase",
        status="active",
    )
    Task.create(
        project_id=project.id,
        id="task-12345",
        title="Test Task 1",
        phase=phase.title,
        phase_id=phase.id,
    )

    # Mock context builders to verify they receive project ID or task ID
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
    monkeypatch.setattr(
        "engram.services.context_service.context.get_task_context",
        lambda tid: f"task:{tid}",
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

    # Exact task ID resolution
    assert server.resources["engram://task/{task_id}/context"]("task-12345") == "task:task-12345"

    # Unique prefix resolution
    assert server.resources["engram://task/{task_id}/context"]("task-12") == "task:task-12345"

    # Missing task reference raises EngramServiceError (TASK_NOT_FOUND)
    with pytest.raises(EngramServiceError) as raised_missing:
        server.resources["engram://task/{task_id}/context"]("task-999")
    assert raised_missing.value.code == "TASK_NOT_FOUND"

    # Ambiguous task reference raises EngramServiceError (TASK_AMBIGUOUS)
    Task.create(
        project_id=project.id,
        id="task-12777",
        title="Test Task 2",
        phase=phase.title,
        phase_id=phase.id,
    )
    with pytest.raises(EngramServiceError) as raised_ambiguous:
        server.resources["engram://task/{task_id}/context"]("task-12")
    assert raised_ambiguous.value.code == "TASK_AMBIGUOUS"


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

    with pytest.raises(EngramServiceError) as raised_task:
        server.resources["engram://task/{task_id}/context"]("some-task")
    assert raised_task.value.code == "PROJECT_NOT_BOUND"


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
    monkeypatch.setattr(
        "engram.services.context_service.context.get_task_context",
        lambda tid: f"task:{tid}",
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
    server.resources["engram://task/{task_id}/context"]("task1001")

    after_rows = {
        "projects": _table_rows("projects"),
        "tasks": _table_rows("tasks"),
        "phases": _table_rows("phases"),
        "memories": _table_rows("memories"),
    }

    assert after_rows == before_rows


def test_register_tools_registers_expected_fastmcp_tools() -> None:
    """Verify that register_tools registers all six expected tools."""

    class MockServer:
        def __init__(self) -> None:
            self.tools: dict[str, Any] = {}

        def tool(self, **kwargs: Any) -> Any:
            def decorator(func: Any) -> Any:
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    expected_tools = {
        "engram_project_current",
        "engram_task_list",
        "engram_task_get",
        "engram_task_next",
        "engram_memory_search",
    }
    for tool_name in expected_tools:
        assert tool_name in server.tools


def test_mcp_memory_search_tool(tmp_db, monkeypatch) -> None:
    """Verify that engram_memory_search tool operates correctly under mock server."""
    import os

    from engram.models.memory import Memory
    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-tools",
        name="MCP Tools Project",
        summary="Test project for MCP Tools",
        repo_paths=[cwd],
    )

    # Create dummy memories
    Memory.create(
        project_id=project.id,
        id="memo-search-1",
        type="decision",
        title="Decide to use FastMCP",
        content="We choose FastMCP for robust STDIO.",
        tags=["mcp", "decision"],
        level="L2",
    )
    Memory.create(
        project_id=project.id,
        id="memo-search-2",
        type="lesson",
        title="Lessons on FTS SQLite search",
        content="FTS5 extension is great for searching memories.",
        tags=["sqlite", "fts"],
        level="L3",
    )

    class MockServer:
        def __init__(self) -> None:
            self.tools: dict[str, Any] = {}

        def tool(self, **kwargs: Any) -> Any:
            def decorator(func: Any) -> Any:
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_memory_search"]

    # 1. Search without filters
    res = yaml.safe_load(tool())
    assert res["ok"] is True
    assert len(res["memories"]) == 2

    # 2. Search with query filter
    res = yaml.safe_load(tool(query="FastMCP"))
    assert res["ok"] is True
    assert len(res["memories"]) == 1
    assert res["memories"][0]["id"] == "memo-search-1"

    # 3. Search with type filter
    res = yaml.safe_load(tool(type="lesson"))
    assert res["ok"] is True
    assert len(res["memories"]) == 1
    assert res["memories"][0]["id"] == "memo-search-2"

    # 4. Search with tags filter
    res = yaml.safe_load(tool(tags=["mcp"]))
    assert res["ok"] is True
    assert len(res["memories"]) == 1
    assert res["memories"][0]["id"] == "memo-search-1"

    # 5. Search with limit
    res = yaml.safe_load(tool(limit=1))
    assert res["ok"] is True
    assert len(res["memories"]) == 1


def test_load_fastmcp_class_raises_non_mcp_module_not_found(monkeypatch):
    """Verify that a ModuleNotFoundError not related to mcp is raised normally."""
    import importlib

    module = importlib.import_module("engram.mcp.server")

    def _raise_other_module_not_found(_name: str) -> object:
        raise ModuleNotFoundError("No module named 'other'", name="other")

    monkeypatch.setattr(module, "import_module", _raise_other_module_not_found)

    with pytest.raises(ModuleNotFoundError) as exc_info:
        module._load_fastmcp_class()

    assert exc_info.value.name == "other"


def test_load_fastmcp_class_raises_if_fastmcp_missing(monkeypatch):
    """Verify that if FastMCP is missing from the module, it raises RuntimeError."""
    import importlib

    module = importlib.import_module("engram.mcp.server")

    class FakeFastMCPModule:
        pass  # No FastMCP attribute

    monkeypatch.setattr(module, "import_module", lambda x: FakeFastMCPModule())

    with pytest.raises(RuntimeError) as exc_info:
        module._load_fastmcp_class()

    assert "missing mcp.server.fastmcp.FastMCP" in str(exc_info.value)


def test_mcp_server_main_calls_run_stdio_server(monkeypatch):
    """Verify that main() calls run_stdio_server()."""
    import importlib

    module = importlib.import_module("engram.mcp.server")

    mock_run_stdio_server = MagicMock()
    monkeypatch.setattr(module, "run_stdio_server", mock_run_stdio_server)

    module.main()
    mock_run_stdio_server.assert_called_once()


def test_mcp_memory_search_tool_pluralization(tmp_db, monkeypatch):
    """Verify that memory search pluralizes types correctly."""
    import os

    from engram.models.memory import Memory
    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-plural",
        name="MCP Plural Project",
        summary="Test project for MCP pluralization",
        repo_paths=[cwd],
    )

    Memory.create(
        project_id=project.id,
        id="mem-snip",
        type="snippet",
        title="snip",
        content="s",
        tags=[],
        level="L2",
    )
    Memory.create(
        project_id=project.id,
        id="mem-note",
        type="note",
        title="note",
        content="n",
        tags=[],
        level="L2",
    )
    Memory.create(
        project_id=project.id,
        id="mem-issue",
        type="issue",
        title="issue",
        content="i",
        tags=[],
        level="L2",
    )
    Memory.create(
        project_id=project.id,
        id="mem-other",
        type="other",
        title="other",
        content="o",
        tags=[],
        level="L2",
    )

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_memory_search"]

    import yaml

    res = yaml.safe_load(tool())
    assert res["ok"] is True
    # The hint should mention snippets/notes/issues/others
    assert "snippets" in res["hint"]
    assert "notes" in res["hint"]
    assert "issues" in res["hint"]
    assert "others" in res["hint"]


def test_mcp_memory_search_tool_no_memories(tmp_db, monkeypatch):
    """Verify that memory search returns the correct hint when there are no memories."""
    import os

    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-mcp-empty",
        name="MCP Empty Project",
        summary="Test project for empty",
        repo_paths=[cwd],
    )

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_memory_search"]

    import yaml

    res = yaml.safe_load(tool())
    assert res["ok"] is True
    assert "No results. Try broader terms." in res["hint"]


def test_engram_task_done_local_is_same_phase(tmp_db, monkeypatch):
    """Verify that task_done local_is_same_phase falls back to effective phase title when phase_id is missing."""
    import os

    from engram.models.phase import Phase
    from engram.models.project import Project
    from engram.models.task import Task

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-phase",
        name="MCP Phase Project",
        summary="Test project for phase",
        repo_paths=[cwd],
    )

    Phase.create(project_id=project.id, id="ph-1", title="My Phase", status="active")

    Task.create(
        project_id=project.id, id="task-1", title="T1", phase="My Phase", status="in-progress"
    )
    Task.create(project_id=project.id, id="task-2", title="T2", phase="My Phase", status="todo")

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_task_done"]

    import yaml

    res = yaml.safe_load(tool(task_ref="task-1"))
    assert res["ok"] is True


def test_engram_workflow_finish_empty_repo(tmp_db, monkeypatch):
    """Verify that engram_workflow_finish fails if project has no repo_paths."""
    import os

    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-norepo",
        name="MCP NoRepo Project",
        summary="Test project",
        repo_paths=[],  # Empty
    )

    import engram.mcp.tools

    monkeypatch.setattr(
        engram.mcp.tools, "resolve_current_project", lambda: {"id": project.id, "repo_paths": []}
    )

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_workflow_finish"]

    import anyio
    import yaml

    res = yaml.safe_load(anyio.run(tool))
    assert res["ok"] is False
    assert "No repository paths configured" in res["message"]


def test_engram_workflow_finish_service_error(tmp_db, monkeypatch):
    """Verify that engram_workflow_finish handles EngramServiceError."""
    import os

    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-mcp-err",
        name="MCP Err Project",
        summary="Test project",
        repo_paths=[cwd],
    )

    import engram.mcp.tools
    from engram.services.errors import EngramServiceError

    def fake_finish_workflow(*args, **kwargs):
        raise EngramServiceError(code="TEST_ERR", message="Test error")

    monkeypatch.setattr(engram.mcp.tools, "finish_workflow", fake_finish_workflow)

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_workflow_finish"]

    import anyio
    import yaml

    res = yaml.safe_load(anyio.run(tool))
    assert res["ok"] is False
    assert res["error"] == "TEST_ERR"


def test_load_fastmcp_class_no_fastmcp_attribute(monkeypatch):
    """Verify that FastMCP class is checked and handled correctly."""
    import importlib

    module = importlib.import_module("engram.mcp.server")

    class FakeFastMCPModule:
        FastMCP = None  # Set it to None to simulate the failure at line 30

    monkeypatch.setattr(module, "import_module", lambda x: FakeFastMCPModule())

    with pytest.raises(RuntimeError) as exc_info:
        module._load_fastmcp_class()

    assert "missing mcp.server.fastmcp.FastMCP" in str(exc_info.value)


def test_mcp_memory_search_tool_pluralization_fallback(tmp_db, monkeypatch):
    import os

    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-plural-fb",
        name="MCP Plural Project FB",
        summary="Test project for MCP pluralization",
        repo_paths=[cwd],
    )
    # The tool returns constraints/decisions when unique_types is empty or it doesn't match
    # we just need type_plurals to be empty

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    # We create memory but with no type or empty type
    from engram.models.memory import Memory

    Memory.create(
        project_id=project.id,
        id="mem-notype",
        type="",
        title="none",
        content="n",
        tags=[],
        level="L2",
    )

    tool = server.tools["engram_memory_search"]

    import yaml

    res = yaml.safe_load(tool())
    assert res["ok"] is True
    assert "constraints/decisions" in res["hint"]


def test_engram_task_done_local_is_same_phase_no_phase_id(tmp_db, monkeypatch):
    import os

    from engram.models.phase import Phase
    from engram.models.project import Project
    from engram.models.task import Task

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-phase-nophaseid",
        name="MCP Phase Project NoPhaseId",
        summary="Test project for phase",
        repo_paths=[cwd],
    )

    Phase.create(project_id=project.id, id="ph-1", title="My Phase", status="active")

    # One with phase_id, one without phase_id, so it falls back to titles
    Task.create(
        project_id=project.id,
        id="task-1",
        title="T1",
        phase="My Phase",
        phase_id="ph-1",
        status="in-progress",
    )
    Task.create(
        project_id=project.id,
        id="task-2",
        title="T2",
        phase="My Phase",
        phase_id=None,
        status="todo",
    )

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_task_done"]

    import yaml

    res = yaml.safe_load(tool(task_ref="task-1"))
    assert res["ok"] is True


def test_mcp_memory_search_tool_pluralization_constraint(tmp_db, monkeypatch):
    import os

    from engram.models.memory import Memory
    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-plural-c",
        name="MCP Plural C Project",
        summary="Test project for MCP pluralization",
        repo_paths=[cwd],
    )

    Memory.create(
        project_id=project.id,
        id="mem-con",
        type="constraint",
        title="con",
        content="c",
        tags=[],
        level="L2",
    )
    Memory.create(
        project_id=project.id,
        id="mem-les",
        type="lesson",
        title="les",
        content="l",
        tags=[],
        level="L2",
    )
    Memory.create(
        project_id=project.id,
        id="mem-dec",
        type="decision",
        title="dec",
        content="d",
        tags=[],
        level="L2",
    )

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_memory_search"]

    import yaml

    res = yaml.safe_load(tool())
    assert res["ok"] is True
    assert "constraints" in res["hint"]
    assert "lessons" in res["hint"]
    assert "decisions" in res["hint"]


def test_engram_task_done_local_is_same_phase_both_phase_id(tmp_db, monkeypatch):
    import os

    from engram.models.phase import Phase
    from engram.models.project import Project
    from engram.models.task import Task

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-phase-bothphaseid",
        name="MCP Phase Project BothPhaseId",
        summary="Test project for phase",
        repo_paths=[cwd],
    )

    Phase.create(project_id=project.id, id="ph-1", title="My Phase", status="active")

    # Both with phase_id to hit the true branch of the `if`
    Task.create(
        project_id=project.id,
        id="task-1",
        title="T1",
        phase="My Phase",
        phase_id="ph-1",
        status="in-progress",
    )
    Task.create(
        project_id=project.id,
        id="task-2",
        title="T2",
        phase="My Phase",
        phase_id="ph-1",
        status="todo",
    )

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_task_done"]

    import yaml

    res = yaml.safe_load(tool(task_ref="task-1"))
    assert res["ok"] is True


def test_load_fastmcp_class_returns_class(monkeypatch):
    import importlib

    module = importlib.import_module("engram.mcp.server")

    class FakeFastMCPModule:
        FastMCP = "FakeClass"

    monkeypatch.setattr(module, "import_module", lambda x: FakeFastMCPModule())
    assert module._load_fastmcp_class() == "FakeClass"

    # 5. Search with limit
    res = yaml.safe_load(tool(limit=1))
    assert res["ok"] is True
    assert len(res["memories"]) == 1


def test_load_fastmcp_class_raises_non_mcp_module_not_found(monkeypatch):
    """Verify that a ModuleNotFoundError not related to mcp is raised normally."""
    import importlib

    module = importlib.import_module("engram.mcp.server")

    def _raise_other_module_not_found(_name: str) -> object:
        raise ModuleNotFoundError("No module named 'other'", name="other")

    monkeypatch.setattr(module, "import_module", _raise_other_module_not_found)

    with pytest.raises(ModuleNotFoundError) as exc_info:
        module._load_fastmcp_class()

    assert exc_info.value.name == "other"


def test_load_fastmcp_class_raises_if_fastmcp_missing(monkeypatch):
    """Verify that if FastMCP is missing from the module, it raises RuntimeError."""
    import importlib

    module = importlib.import_module("engram.mcp.server")

    class FakeFastMCPModule:
        pass  # No FastMCP attribute

    monkeypatch.setattr(module, "import_module", lambda x: FakeFastMCPModule())

    with pytest.raises(RuntimeError) as exc_info:
        module._load_fastmcp_class()

    assert "missing mcp.server.fastmcp.FastMCP" in str(exc_info.value)


def test_mcp_server_main_calls_run_stdio_server(monkeypatch):
    """Verify that main() calls run_stdio_server()."""
    import importlib

    module = importlib.import_module("engram.mcp.server")

    mock_run_stdio_server = MagicMock()
    monkeypatch.setattr(module, "run_stdio_server", mock_run_stdio_server)

    module.main()
    mock_run_stdio_server.assert_called_once()


def test_mcp_memory_search_tool_pluralization(tmp_db, monkeypatch):
    """Verify that memory search pluralizes types correctly."""
    import os

    from engram.models.memory import Memory
    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-plural",
        name="MCP Plural Project",
        summary="Test project for MCP pluralization",
        repo_paths=[cwd],
    )

    Memory.create(
        project_id=project.id,
        id="mem-snip",
        type="snippet",
        title="snip",
        content="s",
        tags=[],
        level="L2",
    )
    Memory.create(
        project_id=project.id,
        id="mem-note",
        type="note",
        title="note",
        content="n",
        tags=[],
        level="L2",
    )
    Memory.create(
        project_id=project.id,
        id="mem-issue",
        type="issue",
        title="issue",
        content="i",
        tags=[],
        level="L2",
    )
    Memory.create(
        project_id=project.id,
        id="mem-other",
        type="other",
        title="other",
        content="o",
        tags=[],
        level="L2",
    )

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_memory_search"]

    import yaml

    res = yaml.safe_load(tool())
    assert res["ok"] is True
    # The hint should mention snippets/notes/issues/others
    assert "snippets" in res["hint"]
    assert "notes" in res["hint"]
    assert "issues" in res["hint"]
    assert "others" in res["hint"]


def test_mcp_memory_search_tool_no_memories(tmp_db, monkeypatch):
    """Verify that memory search returns the correct hint when there are no memories."""
    import os

    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-mcp-empty",
        name="MCP Empty Project",
        summary="Test project for empty",
        repo_paths=[cwd],
    )

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_memory_search"]

    import yaml

    res = yaml.safe_load(tool())
    assert res["ok"] is True
    assert "No results. Try broader terms." in res["hint"]


def test_engram_task_done_local_is_same_phase(tmp_db, monkeypatch):
    """Verify that task_done local_is_same_phase falls back to effective phase title when phase_id is missing."""
    import os

    from engram.models.phase import Phase
    from engram.models.project import Project
    from engram.models.task import Task

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-phase",
        name="MCP Phase Project",
        summary="Test project for phase",
        repo_paths=[cwd],
    )

    Phase.create(project_id=project.id, id="ph-1", title="My Phase", status="active")

    Task.create(
        project_id=project.id, id="task-1", title="T1", phase="My Phase", status="in-progress"
    )
    Task.create(project_id=project.id, id="task-2", title="T2", phase="My Phase", status="todo")

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_task_done"]

    import yaml

    res = yaml.safe_load(tool(task_ref="task-1"))
    assert res["ok"] is True


def test_engram_workflow_finish_empty_repo(tmp_db, monkeypatch):
    """Verify that engram_workflow_finish fails if project has no repo_paths."""
    import os

    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-norepo",
        name="MCP NoRepo Project",
        summary="Test project",
        repo_paths=[],  # Empty
    )

    import engram.mcp.tools

    monkeypatch.setattr(
        engram.mcp.tools, "resolve_current_project", lambda: {"id": project.id, "repo_paths": []}
    )

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_workflow_finish"]

    import anyio
    import yaml

    res = yaml.safe_load(anyio.run(tool))
    assert res["ok"] is False
    assert "No repository paths configured" in res["message"]


def test_engram_workflow_finish_service_error(tmp_db, monkeypatch):
    """Verify that engram_workflow_finish handles EngramServiceError."""
    import os

    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-mcp-err",
        name="MCP Err Project",
        summary="Test project",
        repo_paths=[cwd],
    )

    import engram.mcp.tools
    from engram.services.errors import EngramServiceError

    def fake_finish_workflow(*args, **kwargs):
        raise EngramServiceError(code="TEST_ERR", message="Test error")

    monkeypatch.setattr(engram.mcp.tools, "finish_workflow", fake_finish_workflow)

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_workflow_finish"]

    import anyio
    import yaml

    res = yaml.safe_load(anyio.run(tool))
    assert res["ok"] is False
    assert res["error"] == "TEST_ERR"


def test_load_fastmcp_class_no_fastmcp_attribute(monkeypatch):
    """Verify that FastMCP class is checked and handled correctly."""
    import importlib

    module = importlib.import_module("engram.mcp.server")

    class FakeFastMCPModule:
        FastMCP = None  # Set it to None to simulate the failure at line 30

    monkeypatch.setattr(module, "import_module", lambda x: FakeFastMCPModule())

    with pytest.raises(RuntimeError) as exc_info:
        module._load_fastmcp_class()

    assert "missing mcp.server.fastmcp.FastMCP" in str(exc_info.value)


def test_mcp_memory_search_tool_pluralization_fallback(tmp_db, monkeypatch):
    import os

    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-plural-fb",
        name="MCP Plural Project FB",
        summary="Test project for MCP pluralization",
        repo_paths=[cwd],
    )
    # The tool returns constraints/decisions when unique_types is empty or it doesn't match
    # we just need type_plurals to be empty

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    # We create memory but with no type or empty type
    from engram.models.memory import Memory

    Memory.create(
        project_id=project.id,
        id="mem-notype",
        type="",
        title="none",
        content="n",
        tags=[],
        level="L2",
    )

    tool = server.tools["engram_memory_search"]

    import yaml

    res = yaml.safe_load(tool())
    assert res["ok"] is True
    assert "constraints/decisions" in res["hint"]


def test_engram_task_done_local_is_same_phase_no_phase_id(tmp_db, monkeypatch):
    import os

    from engram.models.phase import Phase
    from engram.models.project import Project
    from engram.models.task import Task

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-phase-nophaseid",
        name="MCP Phase Project NoPhaseId",
        summary="Test project for phase",
        repo_paths=[cwd],
    )

    Phase.create(project_id=project.id, id="ph-1", title="My Phase", status="active")

    # One with phase_id, one without phase_id, so it falls back to titles
    Task.create(
        project_id=project.id,
        id="task-1",
        title="T1",
        phase="My Phase",
        phase_id="ph-1",
        status="in-progress",
    )
    Task.create(
        project_id=project.id,
        id="task-2",
        title="T2",
        phase="My Phase",
        phase_id=None,
        status="todo",
    )

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_task_done"]

    import yaml

    res = yaml.safe_load(tool(task_ref="task-1"))
    assert res["ok"] is True


def test_mcp_memory_search_tool_pluralization_constraint(tmp_db, monkeypatch):
    import os

    from engram.models.memory import Memory
    from engram.models.project import Project

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-plural-c",
        name="MCP Plural C Project",
        summary="Test project for MCP pluralization",
        repo_paths=[cwd],
    )

    Memory.create(
        project_id=project.id,
        id="mem-con",
        type="constraint",
        title="con",
        content="c",
        tags=[],
        level="L2",
    )
    Memory.create(
        project_id=project.id,
        id="mem-les",
        type="lesson",
        title="les",
        content="l",
        tags=[],
        level="L2",
    )
    Memory.create(
        project_id=project.id,
        id="mem-dec",
        type="decision",
        title="dec",
        content="d",
        tags=[],
        level="L2",
    )

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_memory_search"]

    import yaml

    res = yaml.safe_load(tool())
    assert res["ok"] is True
    assert "constraints" in res["hint"]
    assert "lessons" in res["hint"]
    assert "decisions" in res["hint"]


def test_engram_task_done_local_is_same_phase_both_phase_id(tmp_db, monkeypatch):
    import os

    from engram.models.phase import Phase
    from engram.models.project import Project
    from engram.models.task import Task

    cwd = os.path.abspath("repo/fake-tools-repo")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-mcp-phase-bothphaseid",
        name="MCP Phase Project BothPhaseId",
        summary="Test project for phase",
        repo_paths=[cwd],
    )

    Phase.create(project_id=project.id, id="ph-1", title="My Phase", status="active")

    # Both with phase_id to hit the true branch of the `if`
    Task.create(
        project_id=project.id,
        id="task-1",
        title="T1",
        phase="My Phase",
        phase_id="ph-1",
        status="in-progress",
    )
    Task.create(
        project_id=project.id,
        id="task-2",
        title="T2",
        phase="My Phase",
        phase_id="ph-1",
        status="todo",
    )

    class MockServer:
        def __init__(self) -> None:
            self.tools = {}

        def tool(self, **kwargs):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    tool = server.tools["engram_task_done"]

    import yaml

    res = yaml.safe_load(tool(task_ref="task-1"))
    assert res["ok"] is True


def test_load_fastmcp_class_returns_class(monkeypatch):
    import importlib

    module = importlib.import_module("engram.mcp.server")

    class FakeFastMCPModule:
        FastMCP = "FakeClass"

    monkeypatch.setattr(module, "import_module", lambda x: FakeFastMCPModule())
    assert module._load_fastmcp_class() == "FakeClass"
