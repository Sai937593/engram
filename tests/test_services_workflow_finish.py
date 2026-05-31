"""Tests for finish_workflow service function."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError
from engram.services.workflow_service import finish_workflow
from engram.services.workflow_verification_service import record_workflow_verification
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
        memory_review_outcome="created",
    )
    record_workflow_verification(
        project_id=project.id,
        task_id=task.id,
        passed=True,
        summary="all checks passed",
    )

    git_mock = GitMock()

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = finish_workflow("proj-1", "/tmp/proj-1", commit_type="feat")

    assert res["id"] == "t-1"
    assert res["commit"] == "feat(phase-one): Refactor auth [t-1]"
    assert res["memory_review_outcome"] == "created"

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
        memory_review_outcome="created",
    )
    record_workflow_verification(
        project_id=project.id,
        task_id=task.id,
        passed=True,
        summary="all checks passed",
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
        memory_review_outcome="created",
    )
    record_workflow_verification(
        project_id=project.id,
        task_id=task.id,
        passed=True,
        summary="all checks passed",
    )

    git_mock = GitMock()
    git_mock.commit_returncode = 1
    git_mock.commit_stdout = "nothing to commit, working tree clean"

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = finish_workflow("proj-1", "/tmp/proj-1", commit_type="feat")

    assert res["id"] == "t-1"
    # Task should be marked done
    refreshed = Task.get(task.id)
    assert refreshed is not None
    assert refreshed.status == "done"


def test_finish_workflow_project_not_found(tmp_db: Any) -> None:
    """Verify finish_workflow raises PROJECT_NOT_FOUND when project does not exist."""
    with pytest.raises(EngramServiceError) as exc_info:
        finish_workflow("non-existent", "/tmp/path")

    assert exc_info.value.code == "PROJECT_NOT_FOUND"


def test_finish_workflow_requires_verification(tmp_db: Any) -> None:
    """Verify finish_workflow blocks when no verification exists for the active task."""
    project = Project.create(
        id="proj-1",
        name="Project 1",
        summary="Service testing",
        repo_paths=["/tmp/proj-1"],
    )
    Task.create(
        project_id=project.id,
        id="t-1",
        title="Refactor auth",
        phase="Phase One",
        status="in-progress",
        memory_review_outcome="created",
    )
    with pytest.raises(EngramServiceError) as exc_info:
        finish_workflow("proj-1", "/tmp/proj-1", commit_type="feat")
    assert exc_info.value.code == "VERIFICATION_MISSING"


def test_finish_workflow_failed_verification(tmp_db: Any) -> None:
    """Verify finish_workflow blocks when the latest verification failed."""
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
        memory_review_outcome="created",
    )
    record_workflow_verification(
        project_id=project.id,
        task_id=task.id,
        passed=False,
        summary="unit tests failed",
    )

    with pytest.raises(EngramServiceError) as exc_info:
        finish_workflow("proj-1", "/tmp/proj-1", commit_type="feat")
    assert exc_info.value.code == "VERIFICATION_FAILED"


def test_finish_workflow_stale_verification(tmp_db: Any, tmp_path: Any) -> None:
    """Verify finish_workflow blocks when relevant files were modified after the latest verification."""
    repo_path = str(tmp_path)
    project = Project.create(
        id="proj-1",
        name="Project 1",
        summary="Service testing",
        repo_paths=[repo_path],
    )
    task = Task.create(
        project_id=project.id,
        id="t-1",
        title="Refactor auth",
        phase="Phase One",
        status="in-progress",
        relevant_files=["src/helper.py"],
        memory_review_outcome="created",
    )

    # Create relevant file and record a verification at an older timestamp
    candidate = tmp_path / "src" / "helper.py"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text("print('initial')\n", encoding="utf-8")

    record_workflow_verification(
        project_id=project.id,
        task_id=task.id,
        passed=True,
        summary="all checks passed",
        verified_at="2026-05-31 10:00:00",
    )

    # Set the file modification time to be in the future (compared to verified_at)
    import os

    future_time = 1880000000.0  # in 2029, long after 2026-05-31
    os.utime(candidate, (future_time, future_time))

    git_mock = GitMock()
    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        with pytest.raises(EngramServiceError) as exc_info:
            finish_workflow("proj-1", repo_path, commit_type="feat")
    assert exc_info.value.code == "VERIFICATION_STALE_RELEVANT_CHANGES"


def test_format_finish_success() -> None:
    """Verify format_finish_success produces the correct Markdown-first response."""
    from engram.services.workflow_formatter import format_finish_success

    res = format_finish_success(
        task_id="t-123",
        commit_msg="feat(scope): add feature [t-123]",
        phase_complete=False,
        next_guidance="Stop here. The active task is finished and committed. Await further instructions.",
        task_title="Add Feature",
        memory_review_outcome="created",
    )

    assert res.startswith("# Task Finished")
    assert "Task: `t-123` - Add Feature" in res
    assert "Commit: `feat(scope): add feature [t-123]`" in res
    assert "Phase complete: False" in res
    assert "Memory review outcome: `created`" in res
    assert "## Next action" in res
    assert (
        "Stop here. The active task is finished and committed. Await further instructions." in res
    )


def test_format_finish_blocked() -> None:
    """Verify format_finish_blocked produces the correct Markdown-first response."""
    from engram.services.workflow_formatter import format_finish_blocked

    res = format_finish_blocked(
        task_id="t-123",
        reason="Branch dirty",
        next_guidance="Commit or stash changes before proceeding.",
        task_title="Add Feature",
    )

    assert res.startswith("# Finish Blocked")
    assert "Task: `t-123` - Add Feature" in res
    assert "Reason: Branch dirty" in res
    assert "## Next action" in res
    assert "Commit or stash changes before proceeding." in res


def test_finish_workflow_blocks_without_memory_review_outcome(tmp_db: Any) -> None:
    """Verify finish_workflow blocks when active task lacks memory_review_outcome."""
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
    record_workflow_verification(
        project_id=project.id,
        task_id=task.id,
        passed=True,
        summary="all checks passed",
    )

    with pytest.raises(EngramServiceError) as exc_info:
        finish_workflow("proj-1", "/tmp/proj-1", commit_type="feat")
    assert exc_info.value.code == "MEMORY_REVIEW_OUTCOME_MISSING"
