"""Tests for commit resolution and phase completion in finish_workflow."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from engram.models.project import Project
from engram.models.task import Task
from engram.services.workflow_service import finish_workflow
from tests.test_services_workflow_helpers import GitMock


def test_finish_workflow_commit_type_resolution(tmp_db: Any) -> None:
    """Verify various commit type resolutions work properly."""
    project = Project.create(
        id="proj-1",
        name="Project 1",
        summary="Service testing",
        repo_paths=["/tmp/proj-1"],
    )

    git_mock = GitMock()

    # Case A: Explicit commit type chore
    Task.create(
        project_id=project.id,
        id="t-a",
        title="Tidy workspace",
        phase="Phase One",
        status="in-progress",
    )
    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res_a = finish_workflow("proj-1", "/tmp/proj-1", commit_type="chore")
    assert res_a["commit_msg"].startswith("chore(phase-one):")

    # Case B: Resolution from tags (bug tag -> fix)
    git_mock.calls.clear()
    Task.create(
        project_id=project.id,
        id="t-b",
        title="Crash on null pointer",
        phase="Phase One",
        status="in-progress",
        tags=["bug", "regression"],
    )
    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res_b = finish_workflow("proj-1", "/tmp/proj-1")
    assert res_b["commit_msg"].startswith("fix(phase-one):")

    # Case C: Fallback to feat when no explicit type or tags match
    git_mock.calls.clear()
    Task.create(
        project_id=project.id,
        id="t-c",
        title="New dashboard feature",
        phase="Phase One",
        status="in-progress",
    )
    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res_c = finish_workflow("proj-1", "/tmp/proj-1")
    assert res_c["commit_msg"].startswith("feat(phase-one):")


def test_finish_workflow_phase_complete_detection(tmp_db: Any) -> None:
    """Verify phase_complete is computed correctly based on other tasks in the phase."""
    project = Project.create(
        id="proj-1",
        name="Project 1",
        summary="Service testing",
        repo_paths=["/tmp/proj-1"],
    )
    git_mock = GitMock()

    # Case A: Another task remains in the same phase as todo -> phase_complete = False
    Task.create(
        project_id=project.id,
        id="t-1",
        title="Task 1",
        phase="Phase One",
        status="in-progress",
    )
    Task.create(
        project_id=project.id,
        id="t-2",
        title="Task 2",
        phase="Phase One",
        status="todo",
    )

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res_1 = finish_workflow("proj-1", "/tmp/proj-1", commit_type="feat")
    assert res_1["phase_complete"] is False

    # Case B: Only done/cancelled tasks in the phase -> phase_complete = True
    task_2 = Task.get("t-2")
    assert task_2 is not None
    task_2.update(status="in-progress")

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res_2 = finish_workflow("proj-1", "/tmp/proj-1", commit_type="feat")
    assert res_2["phase_complete"] is True
