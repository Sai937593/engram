"""CLI tests for task list output and status-filter behavior."""

from click.testing import CliRunner

from engram.cli import cli
from engram.models.phase import Phase
from engram.models.task import Task


def make_runner_with_project(monkeypatch, project) -> CliRunner:
    """Return a CliRunner with current-project resolution patched."""
    monkeypatch.setattr("engram.cli.get_current_project", lambda: project)
    return CliRunner()


def test_task_list_shows_effective_status(tmp_db, project, monkeypatch) -> None:
    """task list shows effective blocked status and supports filtering by it."""
    runner = make_runner_with_project(monkeypatch, project)
    dependency = Task.create(project_id=project.id, title="Dep Task", status="todo")
    Task.create(project_id=project.id, title="Sub Task", status="todo", depends_on=dependency.id)

    all_result = runner.invoke(cli, ["task", "list", "--status", "all"])
    assert all_result.exit_code == 0
    assert "blocked (dep)" in all_result.output
    assert "todo" in all_result.output

    blocked_result = runner.invoke(cli, ["task", "list", "--status", "blocked"])
    assert blocked_result.exit_code == 0
    assert "Sub Task" in blocked_result.output
    assert "Dep Task" not in blocked_result.output


def test_task_list_shows_effective_phase(tmp_db, project, monkeypatch) -> None:
    """task list displays phase values through effective phase title rules."""
    runner = make_runner_with_project(monkeypatch, project)
    phase = Phase.create(project_id=project.id, title="Phase Alpha")

    Task.create(
        project_id=project.id,
        title="Task A",
        phase_id=phase.id,
        phase="Legacy Should Not Show",
    )
    Task.create(project_id=project.id, title="Task B", phase="Phase Legacy")
    Task.create(project_id=project.id, title="Task C", phase=None)

    result = runner.invoke(cli, ["task", "list", "--status", "all"])
    assert result.exit_code == 0
    assert "Phase Alpha" in result.output
    assert "Phase Legacy" in result.output
    assert "Legacy Should Not Show" not in result.output
    assert "-" in result.output


def test_task_list_default_todo_filter(tmp_db, project, monkeypatch) -> None:
    """task list defaults to todo-only and can show all with --status all."""
    runner = make_runner_with_project(monkeypatch, project)
    Task.create(project_id=project.id, title="Task Todo", status="todo")
    Task.create(project_id=project.id, title="Task Done", status="done")

    default_result = runner.invoke(cli, ["task", "list"])
    assert default_result.exit_code == 0
    assert "Task Todo" in default_result.output
    assert "Task Done" not in default_result.output

    all_result = runner.invoke(cli, ["task", "list", "--status", "all"])
    assert all_result.exit_code == 0
    assert "Task Todo" in all_result.output
    assert "Task Done" in all_result.output


def test_task_list_all_flag(tmp_db, project, monkeypatch) -> None:
    """task list supports --all and -a to include all statuses."""
    runner = make_runner_with_project(monkeypatch, project)
    Task.create(project_id=project.id, title="Task Todo", status="todo")
    Task.create(project_id=project.id, title="Task Done", status="done")

    all_result = runner.invoke(cli, ["task", "list", "--all"])
    assert all_result.exit_code == 0
    assert "Task Todo" in all_result.output
    assert "Task Done" in all_result.output

    short_result = runner.invoke(cli, ["task", "list", "-a"])
    assert short_result.exit_code == 0
    assert "Task Todo" in short_result.output
    assert "Task Done" in short_result.output


def test_task_list_empty_project_guidance(tmp_db, project, monkeypatch) -> None:
    """task list shows add guidance when no tasks are defined."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["task", "list"])
    assert result.exit_code == 0
    assert "No tasks defined" in result.output
    assert "engram task add" in result.output


def test_task_list_all_completed_guidance(tmp_db, project, monkeypatch) -> None:
    """task list shows completion guidance when all tasks are done/cancelled."""
    runner = make_runner_with_project(monkeypatch, project)
    Task.create(project_id=project.id, title="Done Task", status="done")
    Task.create(project_id=project.id, title="Cancelled Task", status="cancelled")

    result = runner.invoke(cli, ["task", "list"])
    assert result.exit_code == 0
    assert "All tasks complete" in result.output
    assert "engram task add" in result.output
