"""Tests for service package adapter-safety boundaries."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path


def _assert_module_is_adapter_safe(module_name: str, banned_prefixes: tuple[str, ...]) -> None:
    module = importlib.import_module(module_name)
    source = Path(module.__file__).read_text(encoding="utf-8")
    parsed = ast.parse(source)

    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for prefix in banned_prefixes:
                    if alias.name.startswith(prefix):
                        raise AssertionError(
                            f"Module {module_name} imports forbidden module/prefix: {alias.name}"
                        )
        elif isinstance(node, ast.ImportFrom):
            imported_module = node.module or ""
            for prefix in banned_prefixes:
                if imported_module.startswith(prefix):
                    raise AssertionError(
                        f"Module {module_name} imports from forbidden module/prefix: {imported_module}"
                    )


def test_project_service_module_is_adapter_safe():
    banned = ("click", "rich", "engram.cli", "engram.commands", "engram.mcp", "subprocess")
    _assert_module_is_adapter_safe("engram.services.project_service", banned)


def test_project_status_service_module_is_adapter_safe():
    banned = ("click", "rich", "engram.cli", "engram.commands", "engram.mcp", "subprocess")
    _assert_module_is_adapter_safe("engram.services.project_status_service", banned)


def test_workflow_helpers_module_is_adapter_safe():
    banned = ("click", "rich", "engram.cli", "engram.commands", "engram.mcp", "subprocess")
    _assert_module_is_adapter_safe("engram.services.workflow_helpers", banned)


def test_workflow_service_module_is_adapter_safe():
    # Exclude subprocess for workflow_service because it calls git commands to check out/commit code
    banned = ("click", "rich", "engram.cli", "engram.commands", "engram.mcp")
    _assert_module_is_adapter_safe("engram.services.workflow_service", banned)


def test_serializers_module_is_adapter_safe():
    banned = ("click", "rich", "engram.cli", "engram.commands", "engram.mcp", "subprocess")
    _assert_module_is_adapter_safe("engram.services.serializers", banned)


def test_project_path_module_is_adapter_safe():
    banned = ("click", "rich", "engram.cli", "engram.commands", "engram.mcp", "subprocess")
    _assert_module_is_adapter_safe("engram.services.project_path", banned)


def test_errors_module_is_adapter_safe():
    banned = ("click", "rich", "engram.cli", "engram.commands", "engram.mcp", "subprocess")
    _assert_module_is_adapter_safe("engram.services.errors", banned)
