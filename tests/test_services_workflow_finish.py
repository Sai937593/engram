"""Tests for finish_workflow service function."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError
from engram.services.workflow_service import finish_workflow
from tests.test_services_workflow_helpers import GitMock


def test_finish_workflow_happy_path(tmp_db: Any) -> None:
    """Verify finish_workflow successfully stages, commits, pushes, and marks task done."""
    project = Project.create(
        id="proj-1",
        name="Project 1",
        summary="Service testing",
        repo_paths=["/tmp/proj-1"],
    )
    task = Task.create(
        project_id=project.id,
        id="t-1",
        title="Refactor auth",
        phase="Phase One",
        status="in-progress",
    )

    git_mock = GitMock()

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = finish_workflow("proj-1", "/tmp/proj-1", commit_type="feat")

    assert res["task"]["id"] == "t-1"
    assert res["commit_msg"] == "feat(phase-one): Refactor auth [t-1]"
    assert "Pushed successfully" in res["push_output"]

    # Task should be marked done
    refreshed = Task.get(task.id)
    assert refreshed is not None
    assert refreshed.status == "done"

    # Verify git actions executed in order
    expected_calls = [
        ["git", "add", "-A"],
        ["git", "commit", "-m", "feat(phase-one): Refactor auth [t-1]"],
        ["git", "push", "-u", "origin", "HEAD"],
    ]
    # Check that they were called
    for call in expected_calls:
        assert call in git_mock.calls


def test_finish_workflow_no_in_progress_task(tmp_db: Any) -> None:
    """Verify finish_workflow raises NO_TASK_IN_PROGRESS if no task is in-progress."""
    project = Project.create(
        id="proj-1",
        name="Project 1",
        summary="Service testing",
        repo_paths=["/tmp/proj-1"],
    )
    Task.create(project_id=project.id, id="t-1", title="Already done", status="done")

    with pytest.raises(EngramServiceError) as exc_info:
        finish_workflow("proj-1", "/tmp/proj-1")

    assert exc_info.value.code == "NO_TASK_IN_PROGRESS"


def test_finish_workflow_git_push_fails(tmp_db: Any) -> None:
    """Verify that if git push fails, task remains in-progress and exception is raised."""
    project = Project.create(
        id="proj-1",
        name="Project 1",
        summary="Service testing",
        repo_paths=["/tmp/proj-1"],
    )
    task = Task.create(
        project_id=project.id,
        id="t-1",
        title="Refactor auth",
        phase="Phase One",
        status="in-progress",
    )

    git_mock = GitMock()
    git_mock.push_returncode = 1
    git_mock.push_stderr = "remote rejected"

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        with pytest.raises(EngramServiceError) as exc_info:
            finish_workflow("proj-1", "/tmp/proj-1", commit_type="feat")

    assert exc_info.value.code == "GIT_OPERATION_FAILED"
    assert "Git command git push failed" in exc_info.value.message

    # Task status should still be in-progress
    refreshed = Task.get(task.id)
    assert refreshed is not None
    assert refreshed.status == "in-progress"


def test_finish_workflow_nothing_to_commit(tmp_db: Any) -> None:
    """Verify that when git commit fails with 'nothing to commit', it continues successfully."""
    project = Project.create(
        id="proj-1",
        name="Project 1",
        summary="Service testing",
        repo_paths=["/tmp/proj-1"],
    )
    task = Task.create(
        project_id=project.id,
        id="t-1",
        title="Refactor auth",
        phase="Phase One",
        status="in-progress",
    )

    git_mock = GitMock()
    git_mock.commit_returncode = 1
    git_mock.commit_stdout = "nothing to commit, working tree clean"

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = finish_workflow("proj-1", "/tmp/proj-1", commit_type="feat")

    assert res["task"]["id"] == "t-1"
    # Task should be marked done
    refreshed = Task.get(task.id)
    assert refreshed is not None
    assert refreshed.status == "done"


def test_finish_workflow_project_not_found(tmp_db: Any) -> None:
    """Verify finish_workflow raises PROJECT_NOT_FOUND when project does not exist."""
    with pytest.raises(EngramServiceError) as exc_info:
        finish_workflow("non-existent", "/tmp/path")

    assert exc_info.value.code == "PROJECT_NOT_FOUND"
