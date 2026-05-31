"""Tests for verify_workflow service behavior."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError
from engram.services.workflow_service import verify_workflow
from engram.services.workflow_verification_service import get_latest_workflow_verification


def test_verify_workflow_records_pass(tmp_db: Any) -> None:
    project = Project.create(
        id="proj-verify-pass",
        name="Verify Pass Project",
        summary="Service verify pass",
        repo_paths=["/tmp/proj-verify-pass"],
    )
    task = Task.create(
        project_id=project.id,
        id="task-verify-pass",
        title="Run verification",
        status="in-progress",
    )

    responses = [
        SimpleNamespace(returncode=0, stdout="ruff ok", stderr=""),
        SimpleNamespace(returncode=0, stdout="pytest ok", stderr=""),
    ]

    with patch("engram.services.workflow_service.subprocess.run", side_effect=responses):
        res = verify_workflow(project.id, "/tmp/proj-verify-pass")

    assert res["passed"] is True
    assert res["task_id"] == task.id
    latest = get_latest_workflow_verification(project_id=project.id, task_id=task.id)
    assert latest is not None
    assert latest["status"] == "passed"
    assert latest["summary"] == "All local quality checks passed."


def test_verify_workflow_records_failure_with_actionable_target(tmp_db: Any) -> None:
    project = Project.create(
        id="proj-verify-fail",
        name="Verify Fail Project",
        summary="Service verify fail",
        repo_paths=["/tmp/proj-verify-fail"],
    )
    task = Task.create(
        project_id=project.id,
        id="task-verify-fail",
        title="Run verification",
        status="in-progress",
    )

    responses = [
        SimpleNamespace(
            returncode=1,
            stdout="src/engram/services/workflow_service.py:42:1: F401 unused import\nextra line",
            stderr="",
        )
    ]

    with patch("engram.services.workflow_service.subprocess.run", side_effect=responses):
        res = verify_workflow(project.id, "/tmp/proj-verify-fail")

    assert res["passed"] is False
    assert res["actionable_target"] == "src/engram/services/workflow_service.py:42:1"
    assert "First actionable target" in res["summary"]
    latest = get_latest_workflow_verification(project_id=project.id, task_id=task.id)
    assert latest is not None
    assert latest["status"] == "failed"
    assert "Check:" in str(latest["details"])


def test_verify_workflow_requires_in_progress_task(tmp_db: Any) -> None:
    project = Project.create(
        id="proj-verify-none",
        name="Verify None Project",
        summary="Service verify no task",
        repo_paths=["/tmp/proj-verify-none"],
    )
    Task.create(project_id=project.id, id="task-done", title="Done", status="done")

    with pytest.raises(EngramServiceError) as exc_info:
        verify_workflow(project.id, "/tmp/proj-verify-none")

    assert exc_info.value.code == "NO_TASK_IN_PROGRESS"
