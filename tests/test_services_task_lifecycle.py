"""Tests for task service lifecycle operations."""

from __future__ import annotations

from typing import Any

import pytest

from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError, ValidationError
from engram.services.task import complete_task, get_next_task, start_task


def _create_project(project_id: str, repo_path: str) -> Project:
    return Project.create(
        id=project_id,
        name=f"Project {project_id}",
        summary="Task service lifecycle tests",
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


def test_start_task_not_found(tmp_db, monkeypatch):
    import engram.services.task.lifecycle as lifecycle

    monkeypatch.setattr(lifecycle, "resolve_task_ref", lambda pid, ref: "missing-task-id")
    project = _create_project("proj-start-nf", "/tmp/proj-start-nf")
    with pytest.raises(EngramServiceError) as exc:
        start_task(project.id, "nonexistent-task")
    assert exc.value.code == "TASK_NOT_FOUND"


def test_start_task_with_dependency_done(tmp_db):
    project = _create_project("proj-start-dep-done", "/tmp/proj-start-dep-done")
    dep = Task.create(project_id=project.id, id="task-dep-01", title="Dep", status="done")
    t = Task.create(
        project_id=project.id, id="task-main-01", title="Main", status="todo", depends_on=dep.id
    )

    dto = start_task(project.id, t.id)
    assert dto["status"] == "in-progress"


def test_start_task_dependency_deleted_from_db(tmp_db):
    project = _create_project("proj-start-dep-del", "/tmp/proj-start-dep-del")
    # Simulate a dependency ID that does not exist in DB (e.g. deleted or dangling ref)
    t = Task.create(
        project_id=project.id,
        id="task-main-02",
        title="Main",
        status="todo",
        depends_on="missing-dep-id",
    )

    dto = start_task(project.id, t.id)
    assert dto["status"] == "in-progress"


def test_complete_task_not_found(tmp_db, monkeypatch):
    import engram.services.task.lifecycle as lifecycle

    monkeypatch.setattr(lifecycle, "resolve_task_ref", lambda pid, ref: "missing-task-id")
    project = _create_project("proj-comp-nf", "/tmp/proj-comp-nf")
    with pytest.raises(EngramServiceError) as exc:
        complete_task(project.id, "nonexistent-task")
    assert exc.value.code == "TASK_NOT_FOUND"


def test_complete_task_appends_evidence(tmp_db):
    project = _create_project("proj-comp-app-ev", "/tmp/proj-comp-app-ev")
    t = Task.create(
        project_id=project.id, id="task-ev-01", title="Task with Ev", status="in-progress"
    )
    t.update(evidence="[2024-01-01 12:00] Old evidence")

    dto = complete_task(project.id, t.id, evidence="New final evidence")
    assert dto["status"] == "done"
    assert "Old evidence" in dto["evidence"]
    assert "New final evidence" in dto["evidence"]
    assert "\n[" in dto["evidence"]
