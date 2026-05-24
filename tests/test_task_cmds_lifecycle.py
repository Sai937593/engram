"""CLI tests for task lifecycle transitions and effective status behavior."""

from click.testing import CliRunner

from engram.cli import cli
from engram.models.task import Task


def make_runner_with_project(monkeypatch, project) -> CliRunner:
    """Return a CliRunner with current-project resolution patched."""
    monkeypatch.setattr("engram.cli.get_current_project", lambda: project)
    return CliRunner()


def test_task_next_no_tasks_defined(tmp_db, project, monkeypatch) -> None:
    """task next shows no-task guidance when the project has zero tasks."""
    runner = make_runner_with_project(monkeypatch, project)
    result = runner.invoke(cli, ["task", "next"])
    assert result.exit_code == 0, result.output
    assert "No tasks defined" in result.output
    assert "engram task add" in result.output


def test_task_next_all_done(tmp_db, project, monkeypatch) -> None:
    """task next shows completion guidance when all tasks are done/cancelled."""
    Task.create(project_id=project.id, title="Done task", status="done")
    Task.create(project_id=project.id, title="Cancelled task", status="cancelled")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["task", "next"])
    assert result.exit_code == 0, result.output
    assert "All tasks complete" in result.output


def test_task_next_all_blocked(tmp_db, project, monkeypatch) -> None:
    """task next shows blocked guidance when all remaining tasks are blocked."""
    Task.create(project_id=project.id, title="Blocked task", status="blocked")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["task", "next"])
    assert result.exit_code == 0, result.output
    assert "blocked" in result.output.lower()


def test_task_next_returns_task(tmp_db, project, monkeypatch) -> None:
    """task next returns the highest-priority actionable task."""
    Task.create(project_id=project.id, title="Ready task", status="todo", priority="high")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["task", "next"])
    assert result.exit_code == 0, result.output
    assert "Ready task" in result.output


def test_task_status_propagation_effective_status(tmp_db, project) -> None:
    """get_effective_status computes transitive status across dependency DAGs."""
    from engram.cli.task_cmds import get_effective_status

    first = Task.create(project_id=project.id, title="T1", status="todo")
    assert get_effective_status(first) == "todo"

    first.update(status="in-progress")
    assert get_effective_status(first) == "in-progress"

    second = Task.create(project_id=project.id, title="T2", status="todo", depends_on=first.id)
    assert get_effective_status(second) == "blocked"

    third = Task.create(project_id=project.id, title="T3", status="todo", depends_on=second.id)
    assert get_effective_status(third) == "blocked"

    first.update(status="cancelled")
    assert get_effective_status(second) == "cancelled"
    assert get_effective_status(third) == "cancelled"

    first.update(status="blocked")
    assert get_effective_status(second) == "blocked"
    assert get_effective_status(third) == "blocked"

    first.update(status="done")
    second.update(status="done")
    third.update(status="todo")
    assert get_effective_status(third) == "todo"


def test_task_start_blocked_by_dependency(tmp_db, project, monkeypatch) -> None:
    """task start is rejected while transitive dependencies are unfinished."""
    runner = make_runner_with_project(monkeypatch, project)
    dependency = Task.create(project_id=project.id, title="Dep Task", status="todo")
    dependent = Task.create(
        project_id=project.id, title="Sub Task", status="todo", depends_on=dependency.id
    )

    blocked_result = runner.invoke(cli, ["task", "start", dependent.id])
    assert "Error:" in blocked_result.output
    assert "blocked by unfinished" in blocked_result.output
    assert f"'{dependency.id}'" in blocked_result.output
    assert Task.get(dependent.id).status == "todo"

    dependency.update(status="done")

    started_result = runner.invoke(cli, ["task", "start", dependent.id])
    assert started_result.exit_code == 0
    assert "marked as in-progress" in started_result.output
    assert Task.get(dependent.id).status == "in-progress"


def test_task_done_blocked_by_dependency(tmp_db, project, monkeypatch) -> None:
    """task done is rejected while transitive dependencies are unfinished."""
    runner = make_runner_with_project(monkeypatch, project)
    dependency = Task.create(project_id=project.id, title="Dep Task", status="todo")
    dependent = Task.create(
        project_id=project.id, title="Sub Task", status="todo", depends_on=dependency.id
    )

    result = runner.invoke(cli, ["task", "done", dependent.id])
    assert "Error:" in result.output
    assert "blocked by unfinished" in result.output
    assert f"'{dependency.id}'" in result.output
    assert Task.get(dependent.id).status == "todo"


def test_task_next_shows_implicit_blockers_count(tmp_db, project, monkeypatch) -> None:
    """task next reports explicit plus implicit blocked counts."""
    runner = make_runner_with_project(monkeypatch, project)
    dependency = Task.create(project_id=project.id, title="Dep Task", status="blocked")
    Task.create(project_id=project.id, title="Sub Task", status="todo", depends_on=dependency.id)

    result = runner.invoke(cli, ["task", "next"])
    assert result.exit_code == 0
    assert "All remaining tasks are blocked" in result.output
    assert "2 blocked" in result.output
