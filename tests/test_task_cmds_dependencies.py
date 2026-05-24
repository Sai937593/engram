"""CLI tests for task dependency resolution and task get/update behavior."""

import re

from click.testing import CliRunner

from engram.cli import cli
from engram.models.phase import Phase
from engram.models.task import Task


def make_runner_with_project(monkeypatch, project) -> CliRunner:
    """Return a CliRunner with current-project resolution patched."""
    monkeypatch.setattr("engram.cli.get_current_project", lambda: project)
    return CliRunner()


def test_task_add_depends_on_exact_and_prefix(tmp_db, project, monkeypatch) -> None:
    """task add supports --depends-on with exact ID and partial prefix."""
    runner = make_runner_with_project(monkeypatch, project)
    dependency = Task.create(project_id=project.id, title="Dependency task")

    result = runner.invoke(cli, ["task", "add", "Task A", "--depends-on", dependency.id])
    assert result.exit_code == 0, result.output
    match = re.search(r"Task created with ID:\s*([a-f0-9]{8})", result.output)
    assert match is not None
    created_exact = Task.get(match.group(1))
    assert created_exact.depends_on == dependency.id

    prefix = dependency.id[:4]
    result_prefix = runner.invoke(cli, ["task", "add", "Task B", "-d", prefix])
    assert result_prefix.exit_code == 0, result_prefix.output
    match_prefix = re.search(r"Task created with ID:\s*([a-f0-9]{8})", result_prefix.output)
    assert match_prefix is not None
    created_prefix = Task.get(match_prefix.group(1))
    assert created_prefix.depends_on == dependency.id


def test_task_add_depends_on_errors(tmp_db, project, monkeypatch) -> None:
    """task add reports missing and ambiguous dependency references."""
    runner = make_runner_with_project(monkeypatch, project)

    missing_result = runner.invoke(cli, ["task", "add", "Task A", "-d", "nonexist"])
    assert missing_result.exit_code != 0
    assert "Error: Task dependency 'nonexist' not found" in missing_result.output

    from engram.db import get_db_connection

    conn = get_db_connection(tmp_db)
    conn.execute(
        "INSERT INTO tasks (id, project_id, title) VALUES ('aaaa1111', ?, 'Task 1')",
        (project.id,),
    )
    conn.execute(
        "INSERT INTO tasks (id, project_id, title) VALUES ('aaaa2222', ?, 'Task 2')",
        (project.id,),
    )
    conn.commit()
    conn.close()

    ambiguous_result = runner.invoke(cli, ["task", "add", "Task B", "-d", "aaaa"])
    assert ambiguous_result.exit_code != 0
    assert "Error: Ambiguous task dependency 'aaaa'" in ambiguous_result.output


def test_task_update_depends_on(tmp_db, project, monkeypatch) -> None:
    """task update manages dependency assignment, self-protection, and clearing."""
    runner = make_runner_with_project(monkeypatch, project)
    first = Task.create(project_id=project.id, title="Task 1")
    second = Task.create(project_id=project.id, title="Task 2")

    assign_result = runner.invoke(
        cli,
        ["task", "update", first.id, "--field", "depends_on", "--value", second.id[:4]],
    )
    assert assign_result.exit_code == 0, assign_result.output
    assert Task.get(first.id).depends_on == second.id

    self_result = runner.invoke(
        cli,
        ["task", "update", first.id, "--field", "depends_on", "--value", first.id[:4]],
    )
    assert self_result.exit_code != 0
    assert "Error: A task cannot depend on itself" in self_result.output

    clear_result = runner.invoke(
        cli,
        ["task", "update", first.id, "--field", "depends_on", "--value", "none"],
    )
    assert clear_result.exit_code == 0, clear_result.output
    assert Task.get(first.id).depends_on is None


def test_task_get_shows_depends_on(tmp_db, project, monkeypatch) -> None:
    """task get displays dependency IDs for dependent tasks."""
    runner = make_runner_with_project(monkeypatch, project)
    dependency = Task.create(project_id=project.id, title="Dep")
    dependent = Task.create(project_id=project.id, title="Main", depends_on=dependency.id)

    dependent_result = runner.invoke(cli, ["task", "get", dependent.id])
    assert dependent_result.exit_code == 0, dependent_result.output
    assert f"Depends On: {dependency.id}" in dependent_result.output

    dependency_result = runner.invoke(cli, ["task", "get", dependency.id])
    assert dependency_result.exit_code == 0, dependency_result.output
    assert "Depends On: N/A" in dependency_result.output


def test_task_get_shows_effective_phase_title(tmp_db, project, monkeypatch) -> None:
    """task get resolves phase display through effective phase title rules."""
    runner = make_runner_with_project(monkeypatch, project)
    phase = Phase.create(project_id=project.id, title="Phase Alpha")

    explicit = Task.create(
        project_id=project.id,
        title="Task Explicit",
        phase_id=phase.id,
        phase="Legacy Should Not Show",
    )
    legacy = Task.create(project_id=project.id, title="Task Legacy", phase="Phase Legacy")
    unphased = Task.create(project_id=project.id, title="Task Unphased")

    explicit_result = runner.invoke(cli, ["task", "get", explicit.id])
    assert explicit_result.exit_code == 0, explicit_result.output
    assert "Phase: Phase Alpha" in explicit_result.output
    assert "Legacy Should Not Show" not in explicit_result.output

    legacy_result = runner.invoke(cli, ["task", "get", legacy.id])
    assert legacy_result.exit_code == 0, legacy_result.output
    assert "Phase: Phase Legacy" in legacy_result.output

    unphased_result = runner.invoke(cli, ["task", "get", unphased.id])
    assert unphased_result.exit_code == 0, unphased_result.output
    assert "Phase: N/A" in unphased_result.output


def test_task_dependency_cycle_detection(tmp_db, project, monkeypatch) -> None:
    """Circular dependencies are rejected and not persisted."""
    runner = make_runner_with_project(monkeypatch, project)

    third = Task.create(project_id=project.id, title="Task C")
    second = Task.create(project_id=project.id, title="Task B", depends_on=third.id)
    first = Task.create(project_id=project.id, title="Task A", depends_on=second.id)

    result = runner.invoke(
        cli,
        ["task", "update", third.id, "--field", "depends_on", "--value", first.id],
    )
    assert result.exit_code != 0
    assert "Error: Circular dependency detected" in result.output
    assert Task.get(third.id).depends_on is None
