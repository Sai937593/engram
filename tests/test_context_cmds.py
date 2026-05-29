"""CLI tests for engram context and export commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from engram.cli import cli
from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError


def make_runner_with_project(monkeypatch: pytest.MonkeyPatch, project: Project) -> CliRunner:
    """Return a CliRunner with project resolution patched for testing."""
    monkeypatch.setattr(
        "engram.services.context_service.project_service.resolve_current_project",
        lambda cwd=None: {
            "id": project.id,
            "name": project.name,
            "summary": project.summary,
            "status": project.status,
            "repo_paths": project.repo_paths,
        },
    )
    return CliRunner()


def test_context_startup_error(tmp_db: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """engram context startup should handle service errors."""

    def mock_get_startup_context() -> str:
        raise EngramServiceError(
            code="MOCK_ERROR",
            message="Simulated startup failure",
            details={},
        )

    monkeypatch.setattr(
        "engram.cli.context_cmds.get_startup_context_for_current_project",
        mock_get_startup_context,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["context", "startup"])
    assert result.exit_code != 0
    assert "Simulated startup failure" in result.output


def test_context_startup_success(
    tmp_db: Any, project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    """engram context startup should print project startup context."""
    runner = make_runner_with_project(monkeypatch, project)
    result = runner.invoke(cli, ["context", "startup"])
    assert result.exit_code == 0
    assert "Test Project" in result.output
    assert "## PROJECT FRAME" in result.output


def test_context_task_success(
    tmp_db: Any, project: Project, task: Task, monkeypatch: pytest.MonkeyPatch
) -> None:
    """engram context task should print context for the given task."""
    runner = make_runner_with_project(monkeypatch, project)
    result = runner.invoke(cli, ["context", "task", task.id])
    assert result.exit_code == 0
    assert task.title in result.output


def test_context_task_errors(
    tmp_db: Any, project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    """engram context task should fail when task is not found or ambiguous."""
    runner = make_runner_with_project(monkeypatch, project)
    # Test missing task
    res_missing = runner.invoke(cli, ["context", "task", "nonexistent"])
    assert res_missing.exit_code != 0
    assert "Task reference was not found in this project." in res_missing.output

    # Test ambiguous task
    Task.create(project_id=project.id, id="feed1000", title="Task 1")
    Task.create(project_id=project.id, id="feed2000", title="Task 2")
    res_ambiguous = runner.invoke(cli, ["context", "task", "feed"])
    assert res_ambiguous.exit_code != 0
    assert "Task reference is ambiguous in this project." in res_ambiguous.output

    # Test service error
    def _mock_get_task_context(*args: Any, **kwargs: Any) -> str:
        raise EngramServiceError(
            code="SERVICE_ERROR",
            message="Test service error",
        )

    monkeypatch.setattr(
        "engram.cli.context_cmds.get_task_context_for_current_project",
        _mock_get_task_context,
    )
    res_service_error = runner.invoke(cli, ["context", "task", "feed"])
    assert res_service_error.exit_code != 0
    assert "Test service error" in res_service_error.output


@pytest.mark.parametrize("cmd", ["startup", "task", "export-snapshot", "export-handoff"])
def test_unbound_errors(tmp_db: Any, monkeypatch: pytest.MonkeyPatch, cmd: str) -> None:
    """engram context commands should fail clearly when no project is bound."""

    def _unbound(cwd: str | None = None) -> dict[str, Any]:
        raise EngramServiceError(
            code="PROJECT_NOT_BOUND",
            message="No project is bound to the current repository path.",
            details={"cwd": str(cwd)},
        )

    monkeypatch.setattr(
        "engram.services.context_service.project_service.resolve_current_project",
        _unbound,
    )
    runner = CliRunner()
    if cmd == "startup":
        cli_cmd = ["context", "startup"]
    elif cmd == "task":
        cli_cmd = ["context", "task", "dummy"]
    elif cmd == "export-snapshot":
        cli_cmd = ["export", "snapshot"]
    else:
        cli_cmd = ["export", "handoff"]

    result = runner.invoke(cli, cli_cmd)
    assert result.exit_code != 0
    assert "No project is bound to the current repository path." in result.output


@pytest.mark.parametrize("export_type", ["snapshot", "handoff"])
def test_exports(
    tmp_db: Any, project: Project, monkeypatch: pytest.MonkeyPatch, export_type: str
) -> None:
    """engram export commands should write snapshots/handoffs correctly."""
    runner = make_runner_with_project(monkeypatch, project)
    with runner.isolated_filesystem():
        # Custom file
        custom_file = f"custom_{export_type}.md"
        res_custom = runner.invoke(cli, ["export", export_type, "-o", custom_file])
        assert res_custom.exit_code == 0
        assert f"exported to: {custom_file}" in res_custom.output
        content = Path(custom_file).read_text(encoding="utf-8")
        assert "Test Project" in content
        assert (
            "# PROJECT SNAPSHOT" if export_type == "snapshot" else "# PROJECT HANDOFF"
        ) in content

        # Default file
        default_file = "SNAPSHOT.md" if export_type == "snapshot" else "HANDOFF.md"
        res_default = runner.invoke(cli, ["export", export_type])
        assert res_default.exit_code == 0
        assert f"exported to: {default_file}" in res_default.output
        assert Path(default_file).exists()
