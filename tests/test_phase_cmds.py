"""CLI tests for `engram phase add`."""

import os
import re

from click.testing import CliRunner

from engram.cli import cli
from engram.models.phase import Phase
from engram.models.project import Project


def make_runner_with_project(monkeypatch, project) -> CliRunner:
    """Return a CliRunner with current-project resolution patched."""
    monkeypatch.setattr("engram.cli.get_current_project", lambda: project)
    return CliRunner()


def test_phase_add_creates_phase_for_current_project(tmp_db, project, monkeypatch) -> None:
    """phase add should create a phase with provided fields."""
    runner = make_runner_with_project(monkeypatch, project)
    result = runner.invoke(
        cli,
        [
            "phase",
            "add",
            "Phase Alpha",
            "--description",
            "Ship milestone one",
            "--status",
            "active",
            "--acceptance",
            "All milestone tasks completed",
        ],
    )

    assert result.exit_code == 0, result.output
    match = re.search(r"Phase created with ID:\s*([a-f0-9]{8})", result.output)
    assert match is not None
    created = Phase.get(match.group(1))
    assert created is not None
    assert created.project_id == project.id
    assert created.title == "Phase Alpha"
    assert created.description == "Ship milestone one"
    assert created.status == "active"
    assert created.acceptance == "All milestone tasks completed"


def test_phase_add_defaults_order_index_to_next_for_project(tmp_db, project, monkeypatch) -> None:
    """phase add auto-assigns the next order_index within the current project only."""
    other_project = Project.create(
        "other-proj",
        "Other Project",
        repo_paths=[os.path.abspath("/tmp/other-repo")],
    )
    Phase.create(project_id=other_project.id, title="Other", order_index=999)
    Phase.create(project_id=project.id, title="Phase One", order_index=2)

    runner = make_runner_with_project(monkeypatch, project)
    result = runner.invoke(cli, ["phase", "add", "Phase Two"])

    assert result.exit_code == 0, result.output
    match = re.search(r"Phase created with ID:\s*([a-f0-9]{8})", result.output)
    assert match is not None
    created = Phase.get(match.group(1))
    assert created is not None
    assert created.order_index == 3


def test_phase_add_rejects_invalid_status(tmp_db, project, monkeypatch) -> None:
    """phase add should reject statuses outside the supported enum."""
    runner = make_runner_with_project(monkeypatch, project)
    result = runner.invoke(cli, ["phase", "add", "Phase Alpha", "--status", "todo"])

    assert result.exit_code != 0
    assert "Invalid value for '--status'" in result.output


def test_phase_add_rejects_duplicate_normalized_title_in_same_project(
    tmp_db, project, monkeypatch
) -> None:
    """phase add blocks duplicate phase titles after normalization in the same project."""
    Phase.create(project_id=project.id, title="  Phase   Alpha  ")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["phase", "add", "phase alpha"])

    assert result.exit_code != 0
    assert "already exists in this project" in result.output


def test_phase_add_allows_same_title_in_another_project(tmp_db, project, monkeypatch) -> None:
    """phase add permits the same normalized title when it belongs to another project."""
    other_project = Project.create(
        "other-proj",
        "Other Project",
        repo_paths=[os.path.abspath("/tmp/other-repo")],
    )
    Phase.create(project_id=other_project.id, title="Phase Alpha")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["phase", "add", "  phase   alpha  "])

    assert result.exit_code == 0, result.output
    phases = Phase.list_by_project(project.id)
    assert any(phase.title == "phase   alpha" for phase in phases)
