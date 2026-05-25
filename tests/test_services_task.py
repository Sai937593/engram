"""Tests for task service read boundaries."""

from __future__ import annotations

from typing import Any

import pytest

from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError
from engram.services.task_service import get_task, list_tasks, resolve_task_ref


def _create_project(project_id: str, repo_path: str) -> Project:
    return Project.create(
        id=project_id,
        name=f"Project {project_id}",
        summary="Task service tests",
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


def test_resolve_task_ref_returns_exact_id_when_exact_and_prefix_matches_exist(tmp_db):
    project = _create_project("proj-a", "/tmp/proj-a")
    Task.create(project_id=project.id, id="abcd1234", title="Exact task")
    Task.create(project_id=project.id, id="abcd9999", title="Prefix collision")

    resolved = resolve_task_ref(project.id, "abcd1234")

    assert resolved == "abcd1234"


def test_resolve_task_ref_returns_unique_prefix_match(tmp_db):
    project = _create_project("proj-b", "/tmp/proj-b")
    Task.create(project_id=project.id, id="beef1234", title="Unique prefix target")

    resolved = resolve_task_ref(project.id, "beef")

    assert resolved == "beef1234"


def test_resolve_task_ref_raises_task_not_found_for_missing_ref(tmp_db):
    project = _create_project("proj-c", "/tmp/proj-c")
    Task.create(project_id=project.id, id="cafe1234", title="Existing task")

    with pytest.raises(EngramServiceError) as raised:
        resolve_task_ref(project.id, "dead")

    error = raised.value
    assert error.code == "TASK_NOT_FOUND"
    assert error.message == "Task reference was not found in this project."
    assert error.details == {"project_id": project.id, "task_ref": "dead"}


def test_resolve_task_ref_raises_task_ambiguous_for_ambiguous_prefix(tmp_db):
    project = _create_project("proj-d", "/tmp/proj-d")
    Task.create(project_id=project.id, id="feed1000", title="Candidate one")
    Task.create(project_id=project.id, id="feed2000", title="Candidate two")

    with pytest.raises(EngramServiceError) as raised:
        resolve_task_ref(project.id, "feed")

    error = raised.value
    assert error.code == "TASK_AMBIGUOUS"
    assert error.message == "Task reference is ambiguous in this project."
    assert error.details == {
        "project_id": project.id,
        "task_ref": "feed",
        "matches": ["feed1000", "feed2000"],
    }


def test_resolve_task_ref_does_not_resolve_foreign_project_tasks(tmp_db):
    in_scope = _create_project("proj-e", "/tmp/proj-e")
    foreign = _create_project("proj-f", "/tmp/proj-f")
    Task.create(project_id=foreign.id, id="face1234", title="Foreign task")

    with pytest.raises(EngramServiceError) as raised:
        resolve_task_ref(in_scope.id, "face")

    error = raised.value
    assert error.code == "TASK_NOT_FOUND"
    assert error.message == "Task reference was not found in this project."
    assert error.details == {"project_id": in_scope.id, "task_ref": "face"}


def test_list_tasks_defaults_to_todo_effective_status(tmp_db):
    project = _create_project("proj-g", "/tmp/proj-g")
    dependency = Task.create(project_id=project.id, id="depd0001", title="Unfinished dependency")
    Task.create(project_id=project.id, id="todo0001", title="Todo candidate")
    Task.create(
        project_id=project.id,
        id="blok0001",
        title="Blocked by dependency",
        depends_on=dependency.id,
    )
    Task.create(project_id=project.id, id="done0001", title="Completed task", status="done")

    payloads = list_tasks(project.id)

    assert {payload["id"] for payload in payloads} == {"todo0001", "depd0001"}
    assert all(payload["effective_status"] == "todo" for payload in payloads)
    _assert_json_safe(payloads)


def test_list_tasks_supports_status_all(tmp_db):
    project = _create_project("proj-h", "/tmp/proj-h")
    Task.create(project_id=project.id, id="all00001", title="Todo task")
    Task.create(
        project_id=project.id, id="all00002", title="In progress task", status="in-progress"
    )
    Task.create(project_id=project.id, id="all00003", title="Done task", status="done")
    Task.create(project_id=project.id, id="all00004", title="Blocked task", status="blocked")
    Task.create(project_id=project.id, id="all00005", title="Cancelled task", status="cancelled")

    payloads = list_tasks(project.id, status="all")

    assert {payload["id"] for payload in payloads} == {
        "all00001",
        "all00002",
        "all00003",
        "all00004",
        "all00005",
    }
    _assert_json_safe(payloads)


def test_list_tasks_filters_by_effective_status(tmp_db):
    project = _create_project("proj-i", "/tmp/proj-i")
    dependency = Task.create(project_id=project.id, id="depd1001", title="Dependency")
    Task.create(
        project_id=project.id,
        id="blok1001",
        title="Blocked task",
        depends_on=dependency.id,
    )
    Task.create(project_id=project.id, id="todo1001", title="Open todo")

    payloads = list_tasks(project.id, status="blocked")

    assert [payload["id"] for payload in payloads] == ["blok1001"]
    assert payloads[0]["effective_status"] == "blocked"
    _assert_json_safe(payloads)


def test_list_tasks_raises_invalid_task_status(tmp_db):
    project = _create_project("proj-j", "/tmp/proj-j")
    Task.create(project_id=project.id, id="stat0001", title="Task")

    with pytest.raises(EngramServiceError) as raised:
        list_tasks(project.id, status="waiting")

    error = raised.value
    assert error.code == "INVALID_TASK_STATUS"
    assert error.message == "Task status filter is invalid."
    assert error.details == {
        "status": "waiting",
        "allowed_statuses": ["all", "blocked", "cancelled", "done", "in-progress", "todo"],
    }


def test_list_tasks_filters_by_phase_with_first_class_precedence(tmp_db):
    project = _create_project("proj-k", "/tmp/proj-k")
    target_phase = Phase.create(project_id=project.id, id="phase001", title="MCP Phase")
    other_phase = Phase.create(project_id=project.id, id="phase002", title="Other Phase")

    Task.create(
        project_id=project.id,
        id="phas0001",
        title="First-class linked",
        phase=target_phase.title,
        phase_id=target_phase.id,
    )
    Task.create(project_id=project.id, id="phas0002", title="Legacy linked", phase="  mcp   phase ")
    Task.create(
        project_id=project.id,
        id="phas0003",
        title="Different first-class phase",
        phase=target_phase.title,
        phase_id=other_phase.id,
    )

    by_id = list_tasks(project.id, status="all", phase=target_phase.id)
    by_title = list_tasks(project.id, status="all", phase=target_phase.title)

    assert {payload["id"] for payload in by_id} == {"phas0001", "phas0002"}
    assert {payload["id"] for payload in by_title} == {"phas0001", "phas0002"}
    _assert_json_safe(by_id)
    _assert_json_safe(by_title)


def test_list_tasks_filters_by_legacy_phase_text_when_no_first_class_match(tmp_db):
    project = _create_project("proj-l", "/tmp/proj-l")
    Task.create(
        project_id=project.id, id="leg00001", title="Legacy phase task", phase="Legacy Lane"
    )
    Task.create(project_id=project.id, id="leg00002", title="Unphased task")

    payloads = list_tasks(project.id, status="all", phase=" legacy   lane ")

    assert [payload["id"] for payload in payloads] == ["leg00001"]
    _assert_json_safe(payloads)


def test_get_task_returns_json_safe_payload_from_scoped_reference(tmp_db):
    project = _create_project("proj-m", "/tmp/proj-m")
    task_item = Task.create(
        project_id=project.id,
        id="gett0001",
        title="Fetch me",
        description="Task details",
        tags=["svc", "mcp"],
        relevant_files=["src/engram/services/task_service.py"],
    )

    payload = get_task(project.id, "gett")

    assert payload["id"] == task_item.id
    assert payload["project_id"] == project.id
    assert payload["title"] == "Fetch me"
    assert payload["effective_status"] == "todo"
    _assert_json_safe(payload)
