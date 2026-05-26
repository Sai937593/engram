"""Tests for MCP adapter package boundaries and startup bootstrap."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

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
