"""Basic tests for start_workflow service function."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError
from engram.services.workflow_service import start_workflow
from tests.test_services_workflow_helpers import GitMock


def test_start_workflow_happy_path_branch_exists(tmp_db: Any, mock_startup_context: None) -> None:
    """Verify start_workflow successfully starts a task when branch already exists."""
    project = Project.create(
        id="proj-1",
        name="Project 1",
        summary="Service testing",
        repo_paths=["/tmp/proj-1"],
    )
    Phase.create(project_id=project.id, id="ph-1", title="Phase One", status="active")
    task = Task.create(
        project_id=project.id,
        id="t-1",
        title="Fix bugs",
        phase="Phase One",
        phase_id="ph-1",
        status="todo",
    )

    git_mock = GitMock()
    git_mock.branch = "main"
    git_mock.status = ""
    git_mock.show_ref_returncode = 0

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = start_workflow("proj-1", "/tmp/proj-1")

    assert res["task"]["id"] == "t-1"
    assert res["branch"] == "feat/phase-phase-one"
    assert res["is_resuming"] is False
    assert res["context"] == "mock startup context string"

    # Task status should be updated to in-progress
    refreshed_task = Task.get(task.id)
    assert refreshed_task is not None
    assert refreshed_task.status == "in-progress"

    # Checkout target branch should be called
    assert ["git", "checkout", "feat/phase-phase-one"] in git_mock.calls
    assert ["git", "checkout", "-b", "feat/phase-phase-one"] not in git_mock.calls


def test_start_workflow_happy_path_new_branch(tmp_db: Any, mock_startup_context: None) -> None:
    """Verify start_workflow successfully starts a task on a new branch if branch doesn't exist."""
    Project.create(
        id="proj-1",
        name="Project 1",
        summary="Service testing",
        repo_paths=["/tmp/proj-1"],
    )
    Phase.create(project_id="proj-1", id="ph-1", title="Phase One", status="active")
    Task.create(
        project_id="proj-1",
        id="t-1",
        title="Fix bugs",
        phase="Phase One",
        phase_id="ph-1",
        status="todo",
    )

    git_mock = GitMock()
    git_mock.branch = "main"
    git_mock.status = ""
    # show-ref verify failing means branch does not exist locally
    git_mock.show_ref_returncode = 1

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = start_workflow("proj-1", "/tmp/proj-1")

    assert res["branch"] == "feat/phase-phase-one"
    assert ["git", "checkout", "-b", "feat/phase-phase-one"] in git_mock.calls


def test_start_workflow_no_task(tmp_db: Any, mock_startup_context: None) -> None:
    """Verify start_workflow handles no actionable tasks cleanly."""
    Project.create(
        id="proj-1",
        name="Project 1",
        summary="Service testing",
        repo_paths=["/tmp/proj-1"],
    )

    git_mock = GitMock()
    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = start_workflow("proj-1", "/tmp/proj-1")

    assert res["task"] is None
    assert res["branch"] is None
    assert res["is_resuming"] is False
    assert res["context"] == "mock startup context string"
    assert len(git_mock.calls) == 0


def test_start_workflow_project_not_found(tmp_db: Any) -> None:
    """Verify start_workflow raises PROJECT_NOT_FOUND when project does not exist."""
    with pytest.raises(EngramServiceError) as exc_info:
        start_workflow("non-existent", "/tmp/path")

    assert exc_info.value.code == "PROJECT_NOT_FOUND"
