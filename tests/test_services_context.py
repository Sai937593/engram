"""Tests for context service read-only wrappers."""

from __future__ import annotations

import ast
import importlib
import os
from pathlib import Path

import pytest

import engram.services.context_service as context_service
from engram.db import get_db_connection
from engram.models.memory import Memory
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task
from engram.services.context_service import (
    get_handoff_context_for_current_project,
    get_snapshot_context_for_current_project,
    get_startup_context_for_current_project,
    get_task_context_for_current_project,
)
from engram.services.errors import EngramServiceError


def _table_rows(table_name: str) -> list[dict[str, object]]:
    conn = get_db_connection()
    rows = conn.execute(f"SELECT * FROM {table_name} ORDER BY rowid ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def test_services_package_exports_context_wrappers():
    services = importlib.import_module("engram.services")
    expected_exports = {
        "get_startup_context_for_current_project",
        "get_snapshot_context_for_current_project",
        "get_handoff_context_for_current_project",
        "get_task_context_for_current_project",
    }

    for export_name in expected_exports:
        assert hasattr(services, export_name)


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
    ("task_id", "task_ref"),
    [
        ("taskx100", "taskx100"),
        ("tasky200", "tasky"),
    ],
)
def test_task_context_wrapper_resolves_project_scoped_task_refs_and_returns_builder_payload(
    tmp_db, monkeypatch, task_id, task_ref
):
    cwd = os.path.abspath(f"repo/{task_id}")
    project = Project.create(
        id=f"proj-{task_id}",
        name=f"Project {task_id}",
        summary="Context wrapper task test",
        repo_paths=[cwd],
    )
    Task.create(project_id=project.id, id=task_id, title="Task context target")
    captured: dict[str, str | None] = {"task_id": None}

    def _task_builder(resolved_task_id: str, hard_constraints_only: bool = False) -> str:
        captured["task_id"] = resolved_task_id
        return f"ctx:{resolved_task_id}"

    monkeypatch.setattr(context_service.context, "get_task_context", _task_builder)

    payload = get_task_context_for_current_project(task_ref=task_ref, cwd=cwd)

    assert payload == f"ctx:{task_id}"
    assert captured["task_id"] == task_id


def test_task_context_wrapper_raises_task_not_found_for_missing_ref(tmp_db):
    cwd = os.path.abspath("repo/missing-task")
    project = Project.create(
        id="proj-missing-task",
        name="Project missing task",
        summary="Context wrapper missing task test",
        repo_paths=[cwd],
    )
    Task.create(project_id=project.id, id="live1000", title="Existing task")

    with pytest.raises(EngramServiceError) as raised:
        get_task_context_for_current_project(task_ref="dead", cwd=cwd)

    error = raised.value
    assert error.code == "TASK_NOT_FOUND"
    assert error.message == "Task reference was not found in this project."
    assert error.details == {"project_id": project.id, "task_ref": "dead"}


def test_task_context_wrapper_raises_task_ambiguous_for_ambiguous_prefix(tmp_db):
    cwd = os.path.abspath("repo/ambiguous-task")
    project = Project.create(
        id="proj-ambiguous-task",
        name="Project ambiguous task",
        summary="Context wrapper ambiguous task test",
        repo_paths=[cwd],
    )
    Task.create(project_id=project.id, id="feed1000", title="Candidate one")
    Task.create(project_id=project.id, id="feed2000", title="Candidate two")

    with pytest.raises(EngramServiceError) as raised:
        get_task_context_for_current_project(task_ref="feed", cwd=cwd)

    error = raised.value
    assert error.code == "TASK_AMBIGUOUS"
    assert error.message == "Task reference is ambiguous in this project."
    assert error.details == {
        "project_id": project.id,
        "task_ref": "feed",
        "matches": ["feed1000", "feed2000"],
    }


def test_task_context_wrapper_does_not_resolve_foreign_project_task_refs(tmp_db):
    in_scope_cwd = os.path.abspath("repo/in-scope")
    foreign_cwd = os.path.abspath("repo/foreign")
    in_scope = Project.create(
        id="proj-in-scope",
        name="In scope",
        summary="In-scope project",
        repo_paths=[in_scope_cwd],
    )
    foreign = Project.create(
        id="proj-foreign",
        name="Foreign",
        summary="Foreign project",
        repo_paths=[foreign_cwd],
    )
    Task.create(project_id=foreign.id, id="face1234", title="Foreign task")

    with pytest.raises(EngramServiceError) as raised:
        get_task_context_for_current_project(task_ref="face", cwd=in_scope_cwd)

    error = raised.value
    assert error.code == "TASK_NOT_FOUND"
    assert error.message == "Task reference was not found in this project."
    assert error.details == {"project_id": in_scope.id, "task_ref": "face"}


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


def test_context_service_wrappers_are_read_only_on_project_task_phase_and_memory_rows(
    tmp_db, monkeypatch
):
    cwd = os.path.abspath("repo/read-only")
    project = Project.create(
        id="proj-read-only",
        name="Project read only",
        summary="Context wrapper read-only coverage",
        repo_paths=[cwd],
    )
    phase = Phase.create(
        project_id=project.id, id="phase1001", title="Active phase", status="active"
    )
    task = Task.create(
        project_id=project.id,
        id="task1001",
        title="Read-only target task",
        phase=phase.title,
        phase_id=phase.id,
    )
    Memory.create(
        project_id=project.id,
        id="memo1001",
        type="note",
        title="Read-only memory",
        content="Ensure wrappers do not write.",
        tags=["read-only"],
        level="L3",
    )
    before_rows = {
        "projects": _table_rows("projects"),
        "tasks": _table_rows("tasks"),
        "phases": _table_rows("phases"),
        "memories": _table_rows("memories"),
    }

    monkeypatch.setattr(
        context_service.context,
        "get_startup_context",
        lambda project_id: f"startup:{project_id}",
    )
    monkeypatch.setattr(
        context_service.context,
        "get_snapshot_context",
        lambda project_id: f"snapshot:{project_id}",
    )
    monkeypatch.setattr(
        context_service.context,
        "get_handoff_context",
        lambda project_id: f"handoff:{project_id}",
    )
    monkeypatch.setattr(
        context_service.context,
        "get_task_context",
        lambda task_id, hard_constraints_only=False: f"task:{task_id}",
    )

    assert get_startup_context_for_current_project(cwd=cwd) == f"startup:{project.id}"
    assert get_snapshot_context_for_current_project(cwd=cwd) == f"snapshot:{project.id}"
    assert get_handoff_context_for_current_project(cwd=cwd) == f"handoff:{project.id}"
    assert get_task_context_for_current_project(task_ref=task.id, cwd=cwd) == f"task:{task.id}"

    after_rows = {
        "projects": _table_rows("projects"),
        "tasks": _table_rows("tasks"),
        "phases": _table_rows("phases"),
        "memories": _table_rows("memories"),
    }

    assert after_rows == before_rows
