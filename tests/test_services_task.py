"""Tests for task service read boundaries."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
from typing import Any

import pytest

from engram.db import get_db_connection
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError, ValidationError
from engram.services.task_service import (
    append_task_note,
    complete_task,
    create_task,
    get_next_task,
    get_task,
    list_tasks,
    resolve_task_ref,
    start_task,
    update_task,
)


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


def _task_rows(project_id: str) -> list[dict[str, object]]:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE project_id = ? ORDER BY id ASC",
        (project_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


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


def test_get_next_task_returns_next_actionable_task_payload(tmp_db):
    project = _create_project("proj-n", "/tmp/proj-n")
    blocked_dependency = Task.create(project_id=project.id, id="depn0001", title="Open dependency")
    Task.create(
        project_id=project.id,
        id="next0001",
        title="Dependency blocked",
        priority="critical",
        depends_on=blocked_dependency.id,
    )
    expected = Task.create(
        project_id=project.id,
        id="next0002",
        title="Next actionable",
        priority="high",
    )

    payload = get_next_task(project.id)

    assert payload is not None
    assert payload["id"] == expected.id
    assert payload["effective_status"] == "todo"
    _assert_json_safe(payload)


def test_get_next_task_returns_none_when_no_actionable_tasks_exist(tmp_db):
    project = _create_project("proj-o", "/tmp/proj-o")
    Task.create(
        project_id=project.id,
        id="next1001",
        title="Blocked by missing dependency",
        depends_on="missing1",
    )
    Task.create(project_id=project.id, id="next1002", title="Done task", status="done")

    payload = get_next_task(project.id)

    assert payload is None


def test_task_service_module_is_adapter_safe(tmp_db):
    module = importlib.import_module("engram.services.task_service")
    source = Path(module.__file__).read_text(encoding="utf-8")
    parsed = ast.parse(source)
    banned_prefixes = ("click", "rich", "engram.commands", "engram.mcp", "subprocess")

    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(banned_prefixes)
        elif isinstance(node, ast.ImportFrom):
            imported_module = node.module or ""
            assert not imported_module.startswith(banned_prefixes)


def test_task_service_calls_are_read_only_on_task_rows(tmp_db):
    project = _create_project("proj-p", "/tmp/proj-p")
    dependency = Task.create(project_id=project.id, id="depp0001", title="Dependency task")
    target = Task.create(
        project_id=project.id,
        id="depp0002",
        title="Target task",
        depends_on=dependency.id,
    )
    before_rows = _task_rows(project.id)

    list_tasks(project.id, status="all")
    get_task(project.id, target.id)
    get_next_task(project.id)

    after_rows = _task_rows(project.id)

    assert after_rows == before_rows


def test_create_task_saves_and_returns_dto(tmp_db):
    project = _create_project("proj-q", "/tmp/proj-q")
    dto = create_task(
        project_id=project.id,
        title="Valid new task",
        description="With description",
        status="in-progress",
        priority="high",
        tags=["t1", "t2"],
        relevant_files=["path/a", "path/b"],
    )

    assert dto["project_id"] == project.id
    assert dto["title"] == "Valid new task"
    assert dto["description"] == "With description"
    assert dto["status"] == "in-progress"
    assert dto["priority"] == "high"
    assert dto["tags"] == ["t1", "t2"]
    assert dto["relevant_files"] == ["path/a", "path/b"]
    assert len(dto["id"]) == 8

    # Verify it actually persisted in the database by fetching it back
    fetched = get_task(project.id, dto["id"])
    assert fetched["id"] == dto["id"]
    assert fetched["title"] == "Valid new task"
    _assert_json_safe(dto)


def test_create_task_invalid_status_raises_validation_error(tmp_db):
    project = _create_project("proj-r", "/tmp/proj-r")
    with pytest.raises(ValidationError) as exc:
        create_task(project_id=project.id, title="Invalid task", status="waiting")

    assert exc.value.code == "INVALID_TASK_STATUS"
    assert "status" in exc.value.details


def test_create_task_invalid_priority_raises_validation_error(tmp_db):
    project = _create_project("proj-s", "/tmp/proj-s")
    with pytest.raises(ValidationError) as exc:
        create_task(project_id=project.id, title="Invalid task", priority="super-critical")

    assert exc.value.code == "INVALID_TASK_PRIORITY"
    assert "priority" in exc.value.details


def test_update_task_happy_path(tmp_db):
    project = _create_project("proj-u", "/tmp/proj-u")
    Task.create(project_id=project.id, id="task0001", title="Original Title", status="todo")

    updated = update_task(
        project_id=project.id,
        task_ref="task0001",
        title="Updated Title",
        status="in-progress",
        priority="high",
        tags=["foo", "bar"],
    )

    assert updated["id"] == "task0001"
    assert updated["title"] == "Updated Title"
    assert updated["status"] == "in-progress"
    assert updated["priority"] == "high"
    assert updated["tags"] == ["foo", "bar"]

    # Verify db persistence
    db_task = get_task(project.id, "task0001")
    assert db_task["title"] == "Updated Title"
    _assert_json_safe(updated)


def test_update_task_rejects_unknown_fields(tmp_db):
    project = _create_project("proj-u", "/tmp/proj-u")
    Task.create(project_id=project.id, id="task0002", title="Task title")

    with pytest.raises(ValidationError) as exc:
        update_task(project_id=project.id, task_ref="task0002", invalid_field_name="some value")

    assert exc.value.code == "UNKNOWN_UPDATE_FIELDS"
    assert "invalid_field_name" in exc.value.details["unknown_fields"]


def test_update_task_invalid_status_and_priority(tmp_db):
    project = _create_project("proj-u", "/tmp/proj-u")
    Task.create(project_id=project.id, id="task0003", title="Task title")

    with pytest.raises(ValidationError) as exc:
        update_task(project_id=project.id, task_ref="task0003", status="invalid_status")
    assert exc.value.code == "INVALID_TASK_STATUS"

    with pytest.raises(ValidationError) as exc:
        update_task(project_id=project.id, task_ref="task0003", priority="invalid_priority")
    assert exc.value.code == "INVALID_TASK_PRIORITY"


def test_update_task_prevents_direct_cycle_and_self_dependency(tmp_db):
    project = _create_project("proj-u", "/tmp/proj-u")
    Task.create(project_id=project.id, id="task0004", title="Task title")

    with pytest.raises(ValidationError) as exc:
        update_task(project_id=project.id, task_ref="task0004", depends_on="task0004")

    assert exc.value.code == "DEPENDENCY_CYCLE"
    assert "cannot depend on itself" in exc.value.message


def test_update_task_prevents_indirect_cycle(tmp_db):
    project = _create_project("proj-u", "/tmp/proj-u")
    Task.create(project_id=project.id, id="task0005", title="Task 5")
    Task.create(project_id=project.id, id="task0006", title="Task 6", depends_on="task0005")

    # Making 5 depend on 6 would create a cycle: 5 -> 6 -> 5
    with pytest.raises(ValidationError) as exc:
        update_task(project_id=project.id, task_ref="task0005", depends_on="task0006")

    assert exc.value.code == "DEPENDENCY_CYCLE"


def test_update_task_first_class_vs_legacy_phase_constraints(tmp_db):
    project = _create_project("proj-u", "/tmp/proj-u")
    Phase.create(project_id=project.id, id="phase001", title="First Class Phase")
    Task.create(project_id=project.id, id="task0007", title="Task 7")

    # Happy path: link to first class phase via phase_id
    updated = update_task(project_id=project.id, task_ref="task0007", phase_id="phase001")
    assert updated["phase_id"] == "phase001"
    assert updated["phase"] == "First Class Phase"

    # Try to change legacy phase text while first class is linked -> ValidationError
    with pytest.raises(ValidationError) as exc:
        update_task(project_id=project.id, task_ref="task0007", phase="New Legacy Title")
    assert exc.value.code == "PHASE_LINKED_TO_FIRST_CLASS"

    # Happy path: clear link by passing phase_id=None
    cleared = update_task(project_id=project.id, task_ref="task0007", phase_id=None)
    assert cleared["phase_id"] is None
    assert cleared["phase"] is None

    # Now we can update legacy phase
    legacy_updated = update_task(
        project_id=project.id, task_ref="task0007", phase="New Legacy Title"
    )
    assert legacy_updated["phase_id"] is None
    assert legacy_updated["phase"] == "New Legacy Title"


def test_append_task_note_happy_path(tmp_db):
    project = _create_project("proj-u", "/tmp/proj-u")
    t = Task.create(project_id=project.id, id="task0008", title="Task 8")
    t.update(evidence="initial note")

    updated = append_task_note(project_id=project.id, task_ref="task0008", note="new progress note")

    assert "initial note" in updated["evidence"]
    assert "new progress note" in updated["evidence"]
    # Check that a timestamp format is prepended: [YYYY-MM-DD HH:MM]
    assert "[" in updated["evidence"]
    assert "]" in updated["evidence"]
    _assert_json_safe(updated)


def test_append_task_note_blank_rejection(tmp_db):
    project = _create_project("proj-u", "/tmp/proj-u")
    Task.create(project_id=project.id, id="task0009", title="Task 9")

    with pytest.raises(ValidationError) as exc:
        append_task_note(project_id=project.id, task_ref="task0009", note="   ")

    assert exc.value.code == "INVALID_NOTE"


def test_start_task_success(tmp_db):
    project = _create_project("proj-start-t", "/tmp/proj-start-t")
    t = Task.create(project_id=project.id, id="task0101", title="Task 101", status="todo")

    dto = start_task(project.id, t.id)
    assert dto["id"] == t.id
    assert dto["status"] == "in-progress"


def test_start_task_fails_if_dependency_unsatisfied(tmp_db):
    project = _create_project("proj-start-t2", "/tmp/proj-start-t2")
    dep = Task.create(project_id=project.id, id="task0102", title="Dependency", status="todo")
    t = Task.create(
        project_id=project.id, id="task0103", title="Task 103", status="todo", depends_on=dep.id
    )

    with pytest.raises(ValidationError) as exc:
        start_task(project.id, t.id)

    assert exc.value.code == "DEPENDENCY_UNSATISFIED"
    assert exc.value.details["depends_on"] == dep.id


def test_complete_task_success_without_evidence(tmp_db):
    project = _create_project("proj-comp-t", "/tmp/proj-comp-t")
    t = Task.create(project_id=project.id, id="task0104", title="Task 104", status="in-progress")

    dto = complete_task(project.id, t.id)
    assert dto["id"] == t.id
    assert dto["status"] == "done"
    assert not dto.get("evidence")


def test_complete_task_success_with_evidence(tmp_db):
    project = _create_project("proj-comp-t2", "/tmp/proj-comp-t2")
    t = Task.create(project_id=project.id, id="task0105", title="Task 105", status="in-progress")

    dto = complete_task(project.id, t.id, evidence="All completed smoothly")
    assert dto["id"] == t.id
    assert dto["status"] == "done"
    assert "All completed smoothly" in dto["evidence"]
    assert "[" in dto["evidence"]
