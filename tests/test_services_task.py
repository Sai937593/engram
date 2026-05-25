"""Tests for task service read boundaries."""

from __future__ import annotations

import pytest

from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError
from engram.services.task_service import resolve_task_ref


def _create_project(project_id: str, repo_path: str) -> Project:
    return Project.create(
        id=project_id,
        name=f"Project {project_id}",
        summary="Task service tests",
        repo_paths=[repo_path],
    )


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
