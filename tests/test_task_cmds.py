"""CLI tests for `engram task` add-phase resolution behavior."""

import re

from click.testing import CliRunner

from engram.cli import cli
from engram.models.phase import Phase
from engram.models.task import Task


def make_runner_with_project(monkeypatch, project) -> CliRunner:
    """Return a CliRunner with current-project resolution patched."""
    monkeypatch.setattr("engram.cli.get_current_project", lambda: project)
    return CliRunner()


def test_task_add_phase_reference_resolves_by_phase_id(tmp_db, project, monkeypatch) -> None:
    """task add --phase <id> should link task.phase_id and mirror legacy task.phase title."""
    phase = Phase.create(project_id=project.id, title="Implementation")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["task", "add", "Wire command", "--phase", phase.id])

    assert result.exit_code == 0, result.output
    assert re.search(r"Task created with ID:\s*[a-f0-9]{8}", result.output)
    created = next(t for t in Task.list_by_project(project.id) if t.title == "Wire command")
    assert created.phase_id == phase.id
    assert created.phase == "Implementation"


def test_task_add_phase_reference_resolves_by_unique_title(tmp_db, project, monkeypatch) -> None:
    """task add --phase <unique title> should resolve within the current project."""
    phase = Phase.create(project_id=project.id, title="Phase   Alpha")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["task", "add", "Use title lookup", "--phase", "  phase alpha  "])

    assert result.exit_code == 0, result.output
    created = next(t for t in Task.list_by_project(project.id) if t.title == "Use title lookup")
    assert created.phase_id == phase.id
    assert created.phase == phase.title


def test_task_add_phase_reference_rejects_ambiguous_title(tmp_db, project, monkeypatch) -> None:
    """task add --phase should fail when normalized title lookup is ambiguous."""
    first = Phase.create(project_id=project.id, title="Phase Alpha")
    second = Phase.create(project_id=project.id, title="  phase   alpha ")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["task", "add", "Ambiguous task", "--phase", "phase alpha"])

    assert result.exit_code != 0
    assert "Ambiguous phase 'phase alpha'" in result.output
    assert first.id in result.output
    assert second.id in result.output


def test_task_add_phase_reference_rejects_missing_phase_id(tmp_db, project, monkeypatch) -> None:
    """task add --phase should error for missing first-class phase identifiers."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["task", "add", "Broken id", "--phase", "deadbeef"])

    assert result.exit_code != 0
    assert "Phase 'deadbeef' not found in this project." in result.output


def test_task_add_phase_preserves_legacy_free_form_when_no_phase_match(
    tmp_db, project, monkeypatch
) -> None:
    """task add keeps legacy free-form phase text when no first-class match exists."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["task", "add", "Legacy task", "--phase", "Backlog Sweep"])

    assert result.exit_code == 0, result.output
    created = next(t for t in Task.list_by_project(project.id) if t.title == "Legacy task")
    assert created.phase_id is None
    assert created.phase == "Backlog Sweep"
