"""Tests for context service read-only wrappers."""

from __future__ import annotations

import ast
import importlib
import os
from pathlib import Path

import pytest

import engram.services.context_service as context_service
from engram.services.context_service import (
    get_handoff_context_for_current_project,
    get_snapshot_context_for_current_project,
    get_startup_context_for_current_project,
)
from engram.services.errors import EngramServiceError


@pytest.mark.parametrize(
    ("wrapper", "builder_name", "expected_payload"),
    [
        (get_startup_context_for_current_project, "get_startup_context", "startup payload"),
        (get_snapshot_context_for_current_project, "get_snapshot_context", "snapshot payload"),
        (get_handoff_context_for_current_project, "get_handoff_context", "handoff payload"),
    ],
)
def test_context_service_project_wrappers_resolve_project_and_return_builder_payload(
    monkeypatch, wrapper, builder_name, expected_payload
):
    captured: dict[str, str | None] = {"cwd": None, "project_id": None}

    def _resolve_current_project(cwd: str | None = None) -> dict[str, str]:
        captured["cwd"] = cwd
        return {"id": "proj-svc-1"}

    def _builder(project_id: str) -> str:
        captured["project_id"] = project_id
        return expected_payload

    monkeypatch.setattr(
        context_service.project_service, "resolve_current_project", _resolve_current_project
    )
    monkeypatch.setattr(context_service.context, builder_name, _builder)

    payload = wrapper(cwd="/tmp/repo-a")

    assert payload == expected_payload
    assert captured == {"cwd": "/tmp/repo-a", "project_id": "proj-svc-1"}


def test_context_service_wrappers_default_cwd_to_project_service(monkeypatch):
    captured: dict[str, str | None] = {"cwd": "sentinel"}

    def _resolve_current_project(cwd: str | None = None) -> dict[str, str]:
        captured["cwd"] = cwd
        return {"id": "proj-svc-2"}

    monkeypatch.setattr(
        context_service.project_service, "resolve_current_project", _resolve_current_project
    )
    monkeypatch.setattr(context_service.context, "get_startup_context", lambda project_id: "ok")

    payload = get_startup_context_for_current_project()

    assert payload == "ok"
    assert captured["cwd"] is None


@pytest.mark.parametrize(
    "wrapper",
    [
        get_startup_context_for_current_project,
        get_snapshot_context_for_current_project,
        get_handoff_context_for_current_project,
    ],
)
def test_context_service_project_wrappers_raise_project_not_bound_for_unbound_repo(tmp_db, wrapper):
    cwd = os.path.abspath("repo/unbound")

    with pytest.raises(EngramServiceError) as raised:
        wrapper(cwd=cwd)

    error = raised.value
    assert error.code == "PROJECT_NOT_BOUND"
    assert error.message == "No project is bound to the current repository path."
    assert error.details == {"cwd": cwd}


def test_context_service_module_is_adapter_safe(tmp_db):
    module = importlib.import_module("engram.services.context_service")
    source = Path(module.__file__).read_text(encoding="utf-8")
    parsed = ast.parse(source)
    banned_prefixes = ("click", "rich", "engram.cli", "engram.commands", "engram.mcp", "subprocess")

    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(banned_prefixes)
        elif isinstance(node, ast.ImportFrom):
            imported_module = node.module or ""
            assert not imported_module.startswith(banned_prefixes)
