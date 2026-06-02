"""Basic tests for start_workflow service function."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from engram.db import get_db_connection, init_db
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
        status="open",
    )

    git_mock = GitMock()
    git_mock.branch = "main"
    git_mock.status = ""
    git_mock.show_ref_returncode = 0

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = start_workflow("proj-1", "/tmp/proj-1")

    assert res["task"]["id"] == "t-1"
    assert res["branch"] == "feat/proj-1-ph-1"
    assert res["is_resuming"] is False
    assert res["context"] == "mock startup context string"

    # Task status should be updated to in_progress
    refreshed_task = Task.get(task.id)
    assert refreshed_task is not None
    assert refreshed_task.status == "in_progress"

    # Checkout target branch should be called
    assert ["git", "checkout", "feat/proj-1-ph-1"] in git_mock.calls
    assert ["git", "checkout", "-b", "feat/proj-1-ph-1"] not in git_mock.calls


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
        status="open",
    )

    git_mock = GitMock()
    git_mock.branch = "main"
    git_mock.status = ""
    # show-ref verify failing means branch does not exist locally
    git_mock.show_ref_returncode = 1

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = start_workflow("proj-1", "/tmp/proj-1")

    assert res["branch"] == "feat/proj-1-ph-1"
    assert ["git", "checkout", "-b", "feat/proj-1-ph-1"] in git_mock.calls


def test_start_workflow_activates_planned_phase_when_starting_first_task(
    tmp_db: Any, mock_startup_context: None
) -> None:
    """Verify starting a task in a planned phase activates that phase."""
    project = Project.create(
        id="proj-phase-start",
        name="Project Phase Start",
        summary="Service testing",
        repo_paths=["/tmp/proj-phase-start"],
    )
    phase = Phase.create(
        project_id=project.id, id="ph-plan-1", title="Planned Phase", status="planned"
    )
    task = Task.create(
        project_id=project.id,
        id="t-plan-1",
        title="Start this phase",
        phase="Planned Phase",
        phase_id=phase.id,
        status="open",
    )

    git_mock = GitMock()
    git_mock.branch = "main"
    git_mock.status = ""
    git_mock.show_ref_returncode = 0

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = start_workflow(project.id, "/tmp/proj-phase-start")

    assert res["task"]["id"] == task.id
    assert res["branch"] == "feat/proj-phase-start-ph-plan-1"
    refreshed_phase = Phase.get(phase.id)
    assert refreshed_phase is not None
    assert refreshed_phase.status == "active"
    refreshed_task = Task.get(task.id)
    assert refreshed_task is not None
    assert refreshed_task.status == "in_progress"


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


def test_start_workflow_blocks_when_only_draft_tasks_remain(
    tmp_db: Any, mock_startup_context: None
) -> None:
    """Verify workflow start blocks with clear code when only draft tasks remain."""
    project = Project.create(
        id="proj-draft-only",
        name="Project Draft Only",
        summary="Service testing",
        repo_paths=["/tmp/proj-draft-only"],
    )
    Task.create(
        project_id=project.id,
        id="t-draft-1",
        title="Draft Task",
        status="draft",
    )

    git_mock = GitMock()
    with (
        patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock),
        pytest.raises(EngramServiceError) as exc_info,
    ):
        start_workflow(project.id, "/tmp/proj-draft-only")

    assert exc_info.value.code == "WORKFLOW_START_DRAFT_ONLY"
    assert "No open task is available to start." in exc_info.value.message
    assert len(git_mock.calls) == 0


def test_start_workflow_project_not_found(tmp_db: Any) -> None:
    """Verify start_workflow raises PROJECT_NOT_FOUND when project does not exist."""
    with pytest.raises(EngramServiceError) as exc_info:
        start_workflow("non-existent", "/tmp/path")

    assert exc_info.value.code == "PROJECT_NOT_FOUND"


def test_start_workflow_unbound_repo(tmp_db: Any, mock_startup_context: None) -> None:
    """Verify start_workflow raises GIT_OPERATION_FAILED when repo_path is not a git repository."""
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
        status="open",
    )

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(EngramServiceError) as exc_info:
            start_workflow("proj-1", tmpdir)

        assert exc_info.value.code == "GIT_OPERATION_FAILED"


def test_start_workflow_picks_task_after_legacy_dependency_normalization(
    tmp_db: Any, mock_startup_context: None
) -> None:
    """Legacy depends_on like '2.3' is normalized during init_db and becomes selectable."""
    project = Project.create(
        id="proj-legacy-dep",
        name="Project Legacy Dep",
        summary="Service testing",
        repo_paths=["/tmp/proj-legacy-dep"],
    )
    Phase.create(project_id=project.id, id="ph-2", title="Phase Two", status="active")

    conn = get_db_connection(tmp_db)
    conn.execute(
        """
        INSERT INTO tasks (id, project_id, title, status, priority, phase, phase_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("dep20001", project.id, "2.3 Prerequisite task", "done", "high", "Phase Two", "ph-2"),
    )
    conn.execute(
        """
        INSERT INTO tasks (id, project_id, title, status, priority, phase, phase_id, depends_on)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("tsk20001", project.id, "2.4 Target task", "open", "high", "Phase Two", "ph-2", "2.3"),
    )
    conn.commit()
    conn.close()

    init_db(tmp_db)

    git_mock = GitMock()
    git_mock.branch = "main"
    git_mock.status = ""
    git_mock.show_ref_returncode = 0

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = start_workflow(project.id, "/tmp/proj-legacy-dep")

    assert res["task"] is not None
    assert res["task"]["id"] == "tsk20001"
