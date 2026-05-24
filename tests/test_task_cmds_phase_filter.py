"""CLI tests for task list phase-filter behavior."""

from click.testing import CliRunner

from engram.cli import cli
from engram.models.phase import Phase
from engram.models.task import Task


def make_runner_with_project(monkeypatch, project) -> CliRunner:
    """Return a CliRunner with current-project resolution patched."""
    monkeypatch.setattr("engram.cli.get_current_project", lambda: project)
    return CliRunner()


def test_task_list_phase_filter_by_id_includes_legacy_matches_only(
    tmp_db, project, monkeypatch
) -> None:
    """task list --phase filters by phase_id and matching legacy-only tasks."""
    runner = make_runner_with_project(monkeypatch, project)
    alpha = Phase.create(project_id=project.id, title="Phase Alpha")
    beta = Phase.create(project_id=project.id, title="Phase Beta")

    Task.create(project_id=project.id, title="AlphaMain", phase_id=alpha.id, phase=alpha.title)
    Task.create(project_id=project.id, title="AlphaLegacy", phase="  phase   alpha ")
    Task.create(project_id=project.id, title="BetaExplicit", phase_id=beta.id, phase=alpha.title)
    Task.create(project_id=project.id, title="NoPhase")

    result = runner.invoke(cli, ["task", "list", "--status", "all", "--phase", alpha.id])
    assert result.exit_code == 0, result.output
    assert "AlphaMain" in result.output
    assert "AlphaLegacy" in result.output
    assert "BetaExplicit" not in result.output
    assert "NoPhase" not in result.output


def test_task_list_phase_filter_by_unique_title_combines_with_status_and_all(
    tmp_db, project, monkeypatch
) -> None:
    """task list --phase title combines correctly with --status and --all."""
    runner = make_runner_with_project(monkeypatch, project)
    alpha = Phase.create(project_id=project.id, title="Phase Alpha")

    Task.create(
        project_id=project.id,
        title="Alpha todo",
        status="todo",
        phase_id=alpha.id,
        phase=alpha.title,
    )
    Task.create(
        project_id=project.id,
        title="Alpha done",
        status="done",
        phase_id=alpha.id,
        phase=alpha.title,
    )
    Task.create(project_id=project.id, title="Other todo", status="todo", phase="Phase Beta")

    default_result = runner.invoke(cli, ["task", "list", "--phase", "  phase alpha  "])
    assert default_result.exit_code == 0, default_result.output
    assert "Alpha todo" in default_result.output
    assert "Alpha done" not in default_result.output
    assert "Other todo" not in default_result.output

    all_result = runner.invoke(cli, ["task", "list", "--phase", "phase alpha", "--all"])
    assert all_result.exit_code == 0, all_result.output
    assert "Alpha todo" in all_result.output
    assert "Alpha done" in all_result.output
    assert "Other todo" not in all_result.output

    done_result = runner.invoke(
        cli,
        ["task", "list", "--phase", "phase alpha", "--status", "done"],
    )
    assert done_result.exit_code == 0, done_result.output
    assert "Alpha done" in done_result.output
    assert "Alpha todo" not in done_result.output
    assert "Other todo" not in done_result.output


def test_task_list_phase_filter_rejects_missing_phase_reference(
    tmp_db, project, monkeypatch
) -> None:
    """task list --phase errors clearly when the phase reference is missing."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["task", "list", "--phase", "missing-phase"])
    assert result.exit_code != 0
    assert "Phase 'missing-phase' not found in this project." in result.output


def test_task_list_phase_filter_rejects_ambiguous_phase_title(tmp_db, project, monkeypatch) -> None:
    """task list --phase errors clearly when title lookup is ambiguous."""
    runner = make_runner_with_project(monkeypatch, project)
    first = Phase.create(project_id=project.id, title="Phase Alpha")
    second = Phase.create(project_id=project.id, title="  phase   alpha ")

    result = runner.invoke(cli, ["task", "list", "--phase", "phase alpha"])
    assert result.exit_code != 0
    assert "Ambiguous phase 'phase alpha'" in result.output
    assert first.id in result.output
    assert second.id in result.output
