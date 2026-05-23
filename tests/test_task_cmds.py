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


def test_task_update_phase_id_by_exact_id(tmp_db, project, monkeypatch) -> None:
    """task update TASK_ID --field phase_id --value PHASE_ID should update phase_id and mirror phase title."""
    phase = Phase.create(project_id=project.id, title="Implementation")
    task = Task.create(project_id=project.id, title="Test Task")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli, ["task", "update", task.id, "--field", "phase_id", "--value", phase.id]
    )

    assert result.exit_code == 0, result.output
    refreshed = Task.get(task.id)
    assert refreshed.phase_id == phase.id
    assert refreshed.phase == "Implementation"


def test_task_update_phase_id_by_unique_title(tmp_db, project, monkeypatch) -> None:
    """task update TASK_ID --field phase_id --value UNIQUE_TITLE should resolve and update."""
    phase = Phase.create(project_id=project.id, title="Phase   Alpha")
    task = Task.create(project_id=project.id, title="Test Task")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli, ["task", "update", task.id, "--field", "phase_id", "--value", "  phase alpha  "]
    )

    assert result.exit_code == 0, result.output
    refreshed = Task.get(task.id)
    assert refreshed.phase_id == phase.id
    assert refreshed.phase == phase.title


def test_task_update_phase_id_rejects_missing(tmp_db, project, monkeypatch) -> None:
    """task update TASK_ID --field phase_id should fail for a missing phase."""
    task = Task.create(project_id=project.id, title="Test Task")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli, ["task", "update", task.id, "--field", "phase_id", "--value", "missing-phase"]
    )

    assert result.exit_code != 0
    assert "Phase 'missing-phase' not found in this project." in result.output


def test_task_update_phase_id_rejects_ambiguous(tmp_db, project, monkeypatch) -> None:
    """task update TASK_ID --field phase_id should fail for ambiguous phase title."""
    first = Phase.create(project_id=project.id, title="Phase Alpha")
    second = Phase.create(project_id=project.id, title="  phase   alpha ")
    task = Task.create(project_id=project.id, title="Test Task")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli, ["task", "update", task.id, "--field", "phase_id", "--value", "phase alpha"]
    )

    assert result.exit_code != 0
    assert "Ambiguous phase 'phase alpha'" in result.output
    assert first.id in result.output
    assert second.id in result.output


def test_task_update_phase_id_clear(tmp_db, project, monkeypatch) -> None:
    """task update TASK_ID --field phase_id --value none/null/clear should clear phase_id and phase."""
    phase = Phase.create(project_id=project.id, title="Implementation")
    task = Task.create(
        project_id=project.id, title="Test Task", phase_id=phase.id, phase=phase.title
    )
    runner = make_runner_with_project(monkeypatch, project)

    for val in ("none", "Null", "CLEAR"):
        result = runner.invoke(
            cli, ["task", "update", task.id, "--field", "phase_id", "--value", val]
        )
        assert result.exit_code == 0, result.output
        refreshed = Task.get(task.id)
        assert refreshed.phase_id is None
        assert refreshed.phase is None


def test_task_update_legacy_phase_unaffected(tmp_db, project, monkeypatch) -> None:
    """task update TASK_ID --field phase --value TEXT should update legacy phase without resolving."""
    task = Task.create(project_id=project.id, title="Test Task")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli, ["task", "update", task.id, "--field", "phase", "--value", "Legacy Sweep"]
    )

    assert result.exit_code == 0, result.output
    refreshed = Task.get(task.id)
    assert refreshed.phase_id is None
    assert refreshed.phase == "Legacy Sweep"


def test_task_next_shows_effective_phase_title_for_phase_id_task(
    tmp_db, project, monkeypatch
) -> None:
    """task next should display the joined phase title for first-class phase_id tasks."""
    phase = Phase.create(project_id=project.id, title="Phase Roadmap")
    Task.create(project_id=project.id, title="Next Task", phase_id=phase.id, priority="high")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["task", "next"])

    assert result.exit_code == 0, result.output
    assert "Title: Next Task" in result.output
    assert "Phase: Phase Roadmap" in result.output
