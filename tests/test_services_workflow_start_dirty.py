"""Tests for start_workflow service function working tree safety."""

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


def test_start_workflow_dirty_tree_branch_mismatch(tmp_db: Any, mock_startup_context: None) -> None:
    """Verify start_workflow raises DIRTY_WORKING_TREE if branch mismatched and working tree is dirty."""
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
    git_mock.status = " M modified_file.py"

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        with pytest.raises(EngramServiceError) as exc_info:
            start_workflow("proj-1", "/tmp/proj-1")

    assert exc_info.value.code == "DIRTY_WORKING_TREE"
    assert "working tree is dirty" in exc_info.value.message

    # Task status should NOT be in-progress
    refreshed = Task.get(task.id)
    assert refreshed is not None
    assert refreshed.status == "todo"


def test_start_workflow_dirty_tree_same_branch(tmp_db: Any, mock_startup_context: None) -> None:
    """Verify start_workflow succeeds when dirty if already on the target branch."""
    project = Project.create(
        id="proj-1",
        name="Project 1",
        summary="Service testing",
        repo_paths=["/tmp/proj-1"],
    )
    Phase.create(project_id=project.id, id="ph-1", title="Phase One", status="active")
    Task.create(
        project_id=project.id,
        id="t-1",
        title="Fix bugs",
        phase="Phase One",
        phase_id="ph-1",
        status="todo",
    )

    git_mock = GitMock()
    git_mock.branch = "feat/phase-phase-one"
    git_mock.status = " M modified_file.py"

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = start_workflow("proj-1", "/tmp/proj-1")

    assert res["task"]["id"] == "t-1"
    assert res["branch"] == "feat/phase-phase-one"


def test_start_workflow_clean_tree_different_branch(
    tmp_db: Any, mock_startup_context: None
) -> None:
    """Verify start_workflow succeeds when tree is clean even if current branch mismatches."""
    project = Project.create(
        id="proj-1",
        name="Project 1",
        summary="Service testing",
        repo_paths=["/tmp/proj-1"],
    )
    Phase.create(project_id=project.id, id="ph-1", title="Phase One", status="active")
    Task.create(
        project_id=project.id,
        id="t-1",
        title="Fix bugs",
        phase="Phase One",
        phase_id="ph-1",
        status="todo",
    )

    git_mock = GitMock()
    git_mock.branch = "some-other-branch"
    git_mock.status = ""

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = start_workflow("proj-1", "/tmp/proj-1")

    assert res["task"]["id"] == "t-1"
    assert res["branch"] == "feat/phase-phase-one"
