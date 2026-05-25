"""Tests for phase service read boundaries."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
from typing import Any

import pytest

from engram.db import get_db_connection
from engram.models.phase import Phase
from engram.models.project import Project
from engram.services.errors import EngramServiceError
from engram.services.phase_service import get_active_phase, list_phases


def _create_project(project_id: str, repo_path: str) -> Project:
    return Project.create(
        id=project_id,
        name=f"Project {project_id}",
        summary="Phase service tests",
        repo_paths=[repo_path],
    )


def _assert_json_safe(value: Any) -> None:
    if value is None or isinstance(value, str | int | float | bool):
        return
    if isinstance(value, list):
        for item in value:
            _assert_json_safe(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str)
            _assert_json_safe(item)
        return
    raise AssertionError(f"Non JSON-safe value encountered: {type(value)!r}")


def _phase_rows(project_id: str) -> list[dict[str, object]]:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM phases WHERE project_id = ? ORDER BY order_index ASC, created_at ASC",
        (project_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def test_list_phases_defaults_to_all_project_phases(tmp_db):
    project = _create_project("proj-phase-a", "/tmp/proj-phase-a")
    Phase.create(project_id=project.id, id="pha00001", title="Planned", status="planned")
    Phase.create(project_id=project.id, id="pha00002", title="Active", status="active")
    Phase.create(project_id=project.id, id="pha00003", title="Done", status="done")

    payloads = list_phases(project.id)

    assert [payload["id"] for payload in payloads] == ["pha00001", "pha00002", "pha00003"]
    _assert_json_safe(payloads)


def test_list_phases_filters_by_status(tmp_db):
    project = _create_project("proj-phase-b", "/tmp/proj-phase-b")
    Phase.create(project_id=project.id, id="phb00001", title="Planned", status="planned")
    Phase.create(project_id=project.id, id="phb00002", title="Blocked", status="blocked")
    Phase.create(project_id=project.id, id="phb00003", title="Blocked 2", status="blocked")

    payloads = list_phases(project.id, status="blocked")

    assert [payload["id"] for payload in payloads] == ["phb00002", "phb00003"]
    assert all(payload["status"] == "blocked" for payload in payloads)
    _assert_json_safe(payloads)


def test_list_phases_supports_status_all(tmp_db):
    project = _create_project("proj-phase-c", "/tmp/proj-phase-c")
    for phase_id, status in [
        ("phc00001", "planned"),
        ("phc00002", "active"),
        ("phc00003", "done"),
        ("phc00004", "blocked"),
        ("phc00005", "cancelled"),
    ]:
        Phase.create(project_id=project.id, id=phase_id, title=f"{status} phase", status=status)

    payloads = list_phases(project.id, status="all")

    assert {payload["status"] for payload in payloads} == {
        "planned",
        "active",
        "done",
        "blocked",
        "cancelled",
    }
    _assert_json_safe(payloads)


def test_list_phases_is_project_scoped(tmp_db):
    target = _create_project("proj-phase-d", "/tmp/proj-phase-d")
    foreign = _create_project("proj-phase-e", "/tmp/proj-phase-e")
    Phase.create(project_id=target.id, id="phd00001", title="Target", status="planned")
    Phase.create(project_id=foreign.id, id="phe00001", title="Foreign", status="active")

    payloads = list_phases(target.id, status="all")

    assert [payload["id"] for payload in payloads] == ["phd00001"]
    assert all(payload["project_id"] == target.id for payload in payloads)
    _assert_json_safe(payloads)


def test_list_phases_raises_invalid_phase_status(tmp_db):
    project = _create_project("proj-phase-f", "/tmp/proj-phase-f")
    Phase.create(project_id=project.id, id="phf00001", title="Any", status="planned")

    with pytest.raises(EngramServiceError) as raised:
        list_phases(project.id, status="queued")

    error = raised.value
    assert error.code == "INVALID_PHASE_STATUS"
    assert error.message == "Phase status filter is invalid."
    assert error.details == {
        "status": "queued",
        "allowed_statuses": ["active", "all", "blocked", "cancelled", "done", "planned"],
    }


def test_get_active_phase_returns_active_phase_payload(tmp_db):
    project = _create_project("proj-phase-g", "/tmp/proj-phase-g")
    Phase.create(project_id=project.id, id="phg00001", title="Planned", status="planned")
    expected = Phase.create(project_id=project.id, id="phg00002", title="Active", status="active")

    payload = get_active_phase(project.id)

    assert payload is not None
    assert payload["id"] == expected.id
    assert payload["project_id"] == project.id
    assert payload["status"] == "active"
    _assert_json_safe(payload)


def test_get_active_phase_returns_none_when_no_active_phase_exists(tmp_db):
    project = _create_project("proj-phase-h", "/tmp/proj-phase-h")
    Phase.create(project_id=project.id, id="phh00001", title="Planned", status="planned")

    payload = get_active_phase(project.id)

    assert payload is None


def test_phase_service_module_is_adapter_safe(tmp_db):
    module = importlib.import_module("engram.services.phase_service")
    source = Path(module.__file__).read_text(encoding="utf-8")
    parsed = ast.parse(source)
    banned_prefixes = ("click", "rich", "engram.cli", "engram.mcp", "subprocess")

    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(banned_prefixes)
        elif isinstance(node, ast.ImportFrom):
            imported_module = node.module or ""
            assert not imported_module.startswith(banned_prefixes)


def test_phase_service_calls_are_read_only_on_phase_rows(tmp_db):
    project = _create_project("proj-phase-i", "/tmp/proj-phase-i")
    Phase.create(project_id=project.id, id="phi00001", title="Active", status="active")
    before_rows = _phase_rows(project.id)

    list_phases(project.id)
    list_phases(project.id, status="active")
    list_phases(project.id, status="all")
    get_active_phase(project.id)

    after_rows = _phase_rows(project.id)

    assert after_rows == before_rows
