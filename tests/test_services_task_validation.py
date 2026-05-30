"""Tests for task service validation logic."""

from __future__ import annotations

import pytest

from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError, ValidationError
from engram.services.task.validation import (
    _check_dependency_cycle,
    _normalize_phase_title,
    _normalize_status,
    resolve_task_ref,
    validate_priority_field,
    validate_status_field,
)


def _create_project(project_id: str, repo_path: str) -> Project:
    return Project.create(
        id=project_id,
        name=f"Project {project_id}",
        summary="Task service tests",
        repo_paths=[repo_path],
    )


def test_resolve_task_ref_returns_exact_id_when_exact_and_prefix_matches_exist(tmp_db):
    project = _create_project("proj-a", "/tmp/proj-a")
    # This specifically hits the "if normalized_ref in matching_ids:" branch
    Task.create(project_id=project.id, id="abcd", title="Exact task")
    Task.create(project_id=project.id, id="abcd1234", title="Prefix collision")

    resolved = resolve_task_ref(project.id, "abcd")

    assert resolved == "abcd"


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


def test_resolve_task_ref_strips_whitespace(tmp_db):
    project = _create_project("proj-w", "/tmp/proj-w")
    Task.create(project_id=project.id, id="test1234", title="Test task")

    resolved = resolve_task_ref(project.id, "  test1234  ")

    assert resolved == "test1234"


def test_check_dependency_cycle_no_op_when_depends_on_is_none(tmp_db):
    project = _create_project("proj-cyc1", "/tmp/proj-cyc1")
    # Should simply return None without error
    _check_dependency_cycle("task1", None, project.id)


def test_check_dependency_cycle_allows_acyclic_graph_with_revisited_nodes(tmp_db):
    project = _create_project("proj-cyc2", "/tmp/proj-cyc2")
    # Setup graph: 1 -> 2, 1 -> 3, 2 -> 4, 3 -> 4
    # Testing updating 1 to depend on 2 (or just re-validating it).
    # Since 2 and 3 both depend on 4, DFS from 1 will visit 4 twice.
    # The 'visited' set optimization prevents redundant checks and infinite loops.
    Task.create(project_id=project.id, id="task4", title="Task 4")
    Task.create(project_id=project.id, id="task3", title="Task 3", depends_on="task4")
    Task.create(project_id=project.id, id="task2", title="Task 2", depends_on="task4")
    Task.create(project_id=project.id, id="task1", title="Task 1", depends_on="task3")

    # Check what happens when task1 also tries to depend on task2
    # Should traverse 1 -> 2 -> 4 and 1 -> 3 -> 4 safely without error
    _check_dependency_cycle("task1", "task2", project.id)


def test_validate_status_field_allows_valid_status():
    validate_status_field("todo")
    validate_status_field("in-progress")


def test_validate_status_field_rejects_all():
    with pytest.raises(ValidationError) as raised:
        validate_status_field("all")
    assert raised.value.code == "INVALID_TASK_STATUS"


def test_validate_status_field_rejects_invalid():
    with pytest.raises(ValidationError) as raised:
        validate_status_field("invalid_status")
    assert raised.value.code == "INVALID_TASK_STATUS"


def test_validate_priority_field_allows_valid():
    validate_priority_field("high")


def test_validate_priority_field_rejects_invalid():
    with pytest.raises(ValidationError) as raised:
        validate_priority_field("super-high")
    assert raised.value.code == "INVALID_TASK_PRIORITY"


def test_normalize_status_returns_todo_for_none():
    assert _normalize_status(None) == "todo"


def test_normalize_status_returns_normalized_valid():
    assert _normalize_status(" IN-PROGRESS ") == "in-progress"


def test_normalize_status_rejects_invalid():
    with pytest.raises(EngramServiceError) as raised:
        _normalize_status("unknown")
    assert raised.value.code == "INVALID_TASK_STATUS"


def test_normalize_phase_title_returns_empty_for_none():
    assert _normalize_phase_title(None) == ""


def test_normalize_phase_title_normalizes_whitespace_and_case():
    assert _normalize_phase_title("  My   PHASE  ") == "my phase"


def test_check_dependency_cycle_hits_visited_cache_early_return(tmp_db):
    project = _create_project("proj-cyc3", "/tmp/proj-cyc3")
    # Setting up a scenario where a node gets fully evaluated (added to visited)
    # and then another path hits that same node.
    # 3 -> 4, 2 -> 4, 1 -> 3
    # Check 1 -> 2, which triggers DFS:
    # Path 1: 1 -> 2 -> 4 (4 is evaluated and added to visited, then 2 added to visited)
    # Path 2: 1 -> 3 -> 4 (when we hit 4, it's already in visited, hitting line 148)
    Task.create(project_id=project.id, id="task4", title="Task 4")
    Task.create(project_id=project.id, id="task3", title="Task 3", depends_on="task4")
    Task.create(project_id=project.id, id="task2", title="Task 2", depends_on="task4")
    Task.create(project_id=project.id, id="task1", title="Task 1", depends_on="task3")

    _check_dependency_cycle("task1", "task2", project.id)


def test_check_dependency_cycle_hits_visited_cache_early_return_again(tmp_db):
    project = _create_project("proj-cyc4", "/tmp/proj-cyc4")
    # Setting up a scenario specifically for `if node in visited: return False`
    Task.create(project_id=project.id, id="leaf", title="Leaf")
    Task.create(project_id=project.id, id="mid1", title="Mid1", depends_on="leaf")
    Task.create(project_id=project.id, id="mid2", title="Mid2", depends_on="leaf")
    Task.create(project_id=project.id, id="root", title="Root", depends_on="mid1")

    # We want root to also depend on mid2 eventually
    # When we validate mid1, it will add leaf to visited
    # When we validate mid2, leaf will be hit and should return False
    _check_dependency_cycle("root", "mid2", project.id)
