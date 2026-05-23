"""CLI tests for `engram phase` commands."""

import os
import re

import pytest
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


def test_phase_list_empty_project(tmp_db, project, monkeypatch) -> None:
    """phase list should show guidance when the current project has no phases."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["phase", "list"])

    assert result.exit_code == 0, result.output
    assert "No phases defined for this project." in result.output


def test_phase_list_single_phase_shows_compact_fields(tmp_db, project, monkeypatch) -> None:
    """phase list should show id/title/status/order with compact summary text."""
    created = Phase.create(
        project_id=project.id,
        title="Phase Alpha",
        status="active",
        order_index=3,
        description="Ship milestone one for onboarding experience",
    )
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["phase", "list"])

    assert result.exit_code == 0, result.output
    assert created.id in result.output
    assert "Phase Alpha" in result.output
    assert "active" in result.output
    assert "3" in result.output
    assert "Ship milestone one for onboarding" in result.output
    assert "experience" in result.output


def test_phase_list_orders_by_order_index_then_creation_order(tmp_db, project, monkeypatch) -> None:
    """phase list should use deterministic ordering by index then creation order."""
    first_same_index = Phase.create(project_id=project.id, title="Build", order_index=1)
    Phase.create(project_id=project.id, title="Plan", order_index=0)
    second_same_index = Phase.create(project_id=project.id, title="Verify", order_index=1)
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["phase", "list"])

    assert result.exit_code == 0, result.output
    plan_pos = result.output.index("Plan")
    first_pos = result.output.index(first_same_index.title)
    second_pos = result.output.index(second_same_index.title)
    assert plan_pos < first_pos < second_pos


def test_phase_list_only_shows_current_project_phases(tmp_db, project, monkeypatch) -> None:
    """phase list should only include phases from the current resolved project."""
    other_project = Project.create(
        "other-proj",
        "Other Project",
        repo_paths=[os.path.abspath("/tmp/other-repo")],
    )
    Phase.create(project_id=project.id, title="Current Project Phase")
    Phase.create(project_id=other_project.id, title="Other Project Phase")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["phase", "list"])

    assert result.exit_code == 0, result.output
    assert "Current Project Phase" in result.output
    assert "Other Project Phase" not in result.output


def test_phase_get_by_id_prints_full_phase_details(tmp_db, project, monkeypatch) -> None:
    """phase get should print full details when phase is referenced by ID."""
    created = Phase.create(
        project_id=project.id,
        title="Phase Alpha",
        status="active",
        order_index=4,
        description="Implement end-to-end command behavior",
        acceptance="All acceptance checks pass",
        evidence="Linked test output",
    )
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["phase", "get", created.id])

    assert result.exit_code == 0, result.output
    assert f"ID: {created.id}" in result.output
    assert "Title: Phase Alpha" in result.output
    assert "Status: active" in result.output
    assert "Order Index: 4" in result.output
    assert "Description: Implement end-to-end command behavior" in result.output
    assert "Acceptance Criteria:" in result.output
    assert "All acceptance checks pass" in result.output
    assert "Evidence / Notes:" in result.output
    assert "Linked test output" in result.output


def test_phase_get_by_unique_normalized_title(tmp_db, project, monkeypatch) -> None:
    """phase get should resolve a unique normalized title within the current project."""
    created = Phase.create(project_id=project.id, title="Phase   Beta")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["phase", "get", "  phase beta  "])

    assert result.exit_code == 0, result.output
    assert f"ID: {created.id}" in result.output
    assert "Title: Phase   Beta" in result.output


def test_phase_get_rejects_ambiguous_normalized_title(tmp_db, project, monkeypatch) -> None:
    """phase get should fail when title lookup matches multiple normalized phases."""
    first = Phase.create(project_id=project.id, title="Phase Alpha")
    second = Phase.create(project_id=project.id, title="  phase   alpha ")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["phase", "get", "phase alpha"])

    assert result.exit_code != 0
    assert "Ambiguous phase 'phase alpha'" in result.output
    assert first.id in result.output
    assert second.id in result.output


def test_phase_get_reports_missing_phase(tmp_db, project, monkeypatch) -> None:
    """phase get should report a clear error when no phase matches."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["phase", "get", "phase zeta"])

    assert result.exit_code != 0
    assert "Phase 'phase zeta' not found in this project." in result.output


@pytest.mark.parametrize(
    ("field", "value", "expected_attr"),
    [
        ("title", "Refined Phase", "Refined Phase"),
        ("description", "Rewritten summary", "Rewritten summary"),
        ("status", "active", "active"),
        ("order_index", "12", 12),
        ("acceptance", "All checks pass", "All checks pass"),
        ("evidence", "CLI output attached", "CLI output attached"),
    ],
)
def test_phase_update_supports_all_mutable_fields(
    tmp_db, project, monkeypatch, field: str, value: str, expected_attr: str | int
) -> None:
    """phase update should apply updates for every mutable phase field."""
    created = Phase.create(
        project_id=project.id,
        title="Initial Phase",
        description="Old summary",
        status="planned",
        order_index=1,
        acceptance="Old acceptance",
        evidence="Old evidence",
    )
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["phase", "update", created.id, "--field", field, "--value", value])

    assert result.exit_code == 0, result.output
    refreshed = Phase.get(created.id)
    assert refreshed is not None
    assert getattr(refreshed, field) == expected_attr
    assert f"Phase '{created.id}' updated." in result.output


def test_phase_update_rejects_unknown_field(tmp_db, project, monkeypatch) -> None:
    """phase update should fail clearly when a field is not mutable."""
    created = Phase.create(project_id=project.id, title="Alpha")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli,
        ["phase", "update", created.id, "--field", "project_id", "--value", "other"],
    )

    assert result.exit_code != 0
    assert "Unknown field 'project_id'" in result.output


def test_phase_update_rejects_invalid_status(tmp_db, project, monkeypatch) -> None:
    """phase update should fail clearly on unsupported status values."""
    created = Phase.create(project_id=project.id, title="Alpha")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli,
        ["phase", "update", created.id, "--field", "status", "--value", "todo"],
    )

    assert result.exit_code != 0
    assert "Invalid status 'todo'" in result.output


def test_phase_update_rejects_non_integer_order_index(tmp_db, project, monkeypatch) -> None:
    """phase update should fail when order_index cannot be parsed as an integer."""
    created = Phase.create(project_id=project.id, title="Alpha")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli,
        ["phase", "update", created.id, "--field", "order_index", "--value", "first"],
    )

    assert result.exit_code != 0
    assert "Invalid order_index 'first'" in result.output


def test_phase_update_title_preserves_project_normalized_uniqueness(
    tmp_db, project, monkeypatch
) -> None:
    """phase update should reject a title that collides by normalized value in the same project."""
    created = Phase.create(project_id=project.id, title="Build")
    Phase.create(project_id=project.id, title="Phase Alpha")
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli,
        ["phase", "update", created.id, "--field", "title", "--value", "  phase   alpha "],
    )

    assert result.exit_code != 0
    assert "already exists in this project" in result.output
