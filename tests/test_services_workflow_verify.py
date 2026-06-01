"""Tests for verify_workflow service behavior."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError
from engram.services.workflow_verification_service import get_latest_workflow_verification
from engram.services.workflow_verify_service import _resolve_verify_commands, verify_workflow


def test_resolve_verify_commands_uses_uv_run_when_uv_lock_exists(tmp_path: Any) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")

    commands = _resolve_verify_commands(str(tmp_path))

    assert commands == [
        ["uv", "run", "ruff", "format", "."],
        ["uv", "run", "ruff", "check", ".", "--fix"],
        ["uv", "run", "python", "-m", "engram.hooks.py_structure"],
        ["uv", "run", "pytest", "tests/", "-m", "not slow", "-x", "--tb=short", "-q"],
    ]


def test_resolve_verify_commands_falls_back_without_uv_lock(tmp_path: Any) -> None:
    commands = _resolve_verify_commands(str(tmp_path))

    assert commands == [
        ["python", "-m", "ruff", "format", "."],
        ["python", "-m", "ruff", "check", ".", "--fix"],
        ["python", "-m", "engram.hooks.py_structure"],
        ["python", "-m", "pytest", "tests/", "-m", "not slow", "-x", "--tb=short", "-q"],
    ]


def test_verify_workflow_records_pass(tmp_db: Any, tmp_path: Any) -> None:
    project = Project.create(
        id="proj-verify-pass",
        name="Verify Pass Project",
        summary="Service verify pass",
        repo_paths=[str(tmp_path)],
    )
    task = Task.create(
        project_id=project.id,
        id="task-verify-pass",
        title="Run verification",
        status="in-progress",
    )

    responses = [
        SimpleNamespace(returncode=0, stdout="ruff ok", stderr=""),
        SimpleNamespace(returncode=0, stdout="ruff check ok", stderr=""),
        SimpleNamespace(returncode=0, stdout="py_structure ok", stderr=""),
        SimpleNamespace(returncode=0, stdout="pytest ok", stderr=""),
    ]

    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    with patch(
        "engram.services.workflow_verify_service.subprocess.run", side_effect=responses
    ) as run_mock:
        res = verify_workflow(project.id, str(tmp_path))

    assert res["passed"] is True
    assert res["task_id"] == task.id
    assert res["summary"] == "All local quality checks passed."
    assert res["actionable_target"] is None
    called = [list(call.args[0]) for call in run_mock.call_args_list]
    assert called == [
        ["uv", "run", "ruff", "format", "."],
        ["uv", "run", "ruff", "check", ".", "--fix"],
        ["uv", "run", "python", "-m", "engram.hooks.py_structure"],
        ["uv", "run", "pytest", "tests/", "-m", "not slow", "-x", "--tb=short", "-q"],
    ]
    latest = get_latest_workflow_verification(project_id=project.id, task_id=task.id)
    assert latest is not None
    assert latest["status"] == "passed"
    assert latest["summary"] == "All local quality checks passed."
    details = str(latest["details"])
    assert "uv run ruff format ." in details
    assert "uv run ruff check . --fix" in details
    assert "uv run python -m engram.hooks.py_structure" in details
    assert 'uv run pytest tests/ -m "not slow" -x --tb=short -q' in details


def test_verify_workflow_records_failure_with_actionable_target(tmp_db: Any, tmp_path: Any) -> None:
    project = Project.create(
        id="proj-verify-fail",
        name="Verify Fail Project",
        summary="Service verify fail",
        repo_paths=[str(tmp_path)],
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

    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    with patch("engram.services.workflow_verify_service.subprocess.run", side_effect=responses):
        res = verify_workflow(project.id, str(tmp_path))

    assert res["passed"] is False
    assert res["actionable_target"] == "src/engram/services/workflow_service.py:42:1"
    assert "First actionable target" in res["summary"]
    assert "`uv run ruff format .` failed." in res["summary"]
    latest = get_latest_workflow_verification(project_id=project.id, task_id=task.id)
    assert latest is not None
    assert latest["status"] == "failed"
    refreshed_task = Task.get(task.id)
    assert refreshed_task is not None
    assert refreshed_task.is_verified is False
    details = str(latest["details"])
    assert "Command: `uv run ruff format .`" in details
    assert "Exit code: 1" in details
    assert "Output tail:" in details
    assert "src/engram/services/workflow_service.py:42:1: F401 unused import" in details
    assert "extra line" in details


def test_verify_workflow_failure_does_not_stage_files(tmp_db: Any, tmp_path: Any) -> None:
    project = Project.create(
        id="proj-verify-fail-no-stage",
        name="Verify Fail No Stage Project",
        summary="Service verify fail no stage",
        repo_paths=[str(tmp_path)],
    )
    Task.create(
        project_id=project.id,
        id="task-verify-fail-no-stage",
        title="Run verification",
        status="in-progress",
    )

    responses = [SimpleNamespace(returncode=1, stdout="bad", stderr="")]
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    with patch(
        "engram.services.workflow_verify_service.subprocess.run", side_effect=responses
    ) as run_mock:
        verify_workflow(project.id, str(tmp_path))

    called = [list(call.args[0]) for call in run_mock.call_args_list]
    assert called == [["uv", "run", "ruff", "format", "."]]
    assert not any(cmd[:2] == ["git", "add"] for cmd in called)


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
