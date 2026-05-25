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


def test_task_update_phase_field_resolves_existing_phase_assignment(
    tmp_db, project, monkeypatch
) -> None:
    """task update --field phase should update first-class phase linkage when value resolves."""
    phase_alpha = Phase.create(project_id=project.id, title="Phase Alpha")
    phase_beta = Phase.create(project_id=project.id, title="Phase Beta")
    task = Task.create(
        project_id=project.id,
        title="Test Task",
        phase_id=phase_alpha.id,
        phase=phase_alpha.title,
    )
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli,
        ["task", "update", task.id, "--field", "phase", "--value", "Phase Beta"],
    )

    assert result.exit_code == 0, result.output
    refreshed = Task.get(task.id)
    assert refreshed.phase_id == phase_beta.id
    assert refreshed.phase == phase_beta.title


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


def test_task_add_accepts_relevant_files_csv(tmp_db, project, monkeypatch) -> None:
    """task add --files stores normalized comma-separated path hints."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli,
        [
            "task",
            "add",
            "Task with files",
            "--files",
            " src/engram/cli/task_cmds.py , tests/test_task_cmds.py ",
        ],
    )

    assert result.exit_code == 0, result.output
    created = next(t for t in Task.list_by_project(project.id) if t.title == "Task with files")
    assert created.relevant_files == ["src/engram/cli/task_cmds.py", "tests/test_task_cmds.py"]


def test_task_add_relevant_files_validation_errors(tmp_db, project, monkeypatch) -> None:
    """task add --files rejects duplicates and blank entries with clear errors."""
    runner = make_runner_with_project(monkeypatch, project)

    duplicate_result = runner.invoke(
        cli,
        ["task", "add", "Duplicate files", "--files", "src/a.py,src/a.py"],
    )
    assert duplicate_result.exit_code != 0
    assert "--files contains duplicate path(s): src/a.py" in duplicate_result.output

    blank_result = runner.invoke(
        cli,
        ["task", "add", "Blank files", "--files", "src/a.py,,tests/b.py"],
    )
    assert blank_result.exit_code != 0
    assert "--files contains blank path entries at position(s): 2" in blank_result.output


def test_task_get_relevant_files_visibility(tmp_db, project, monkeypatch) -> None:
    """task get prints relevant file paths only when metadata is present."""
    runner = make_runner_with_project(monkeypatch, project)
    with_files = Task.create(
        project_id=project.id,
        title="Task With Files",
        relevant_files=["src/engram/models/task.py", "tests/test_task.py"],
    )
    without_files = Task.create(project_id=project.id, title="Task Without Files")

    with_result = runner.invoke(cli, ["task", "get", with_files.id])
    assert with_result.exit_code == 0, with_result.output
    assert "Relevant Files:" in with_result.output
    assert "- src/engram/models/task.py" in with_result.output
    assert "- tests/test_task.py" in with_result.output

    without_result = runner.invoke(cli, ["task", "get", without_files.id])
    assert without_result.exit_code == 0, without_result.output
    assert "Relevant Files:" not in without_result.output


def test_task_files_workflow_list_add_remove(tmp_db, project, monkeypatch) -> None:
    """task files list/add/remove manages relevant path hints on an existing task."""
    runner = make_runner_with_project(monkeypatch, project)
    task_item = Task.create(
        project_id=project.id,
        title="Task File Workflow",
        relevant_files=["src/engram/cli/task_helpers.py"],
    )

    list_result = runner.invoke(cli, ["task", "files", "list", task_item.id])
    assert list_result.exit_code == 0, list_result.output
    assert "Relevant file paths for task" in list_result.output
    assert "- src/engram/cli/task_helpers.py" in list_result.output

    add_result = runner.invoke(
        cli,
        [
            "task",
            "files",
            "add",
            task_item.id,
            "--files",
            "src/engram/cli/task_cmds_query.py,tests/test_task_cmds.py",
        ],
    )
    assert add_result.exit_code == 0, add_result.output
    refreshed_after_add = Task.get(task_item.id)
    assert refreshed_after_add is not None
    assert refreshed_after_add.relevant_files == [
        "src/engram/cli/task_helpers.py",
        "src/engram/cli/task_cmds_query.py",
        "tests/test_task_cmds.py",
    ]

    remove_result = runner.invoke(
        cli,
        ["task", "files", "remove", task_item.id, "--files", "src/engram/cli/task_helpers.py"],
    )
    assert remove_result.exit_code == 0, remove_result.output
    refreshed_after_remove = Task.get(task_item.id)
    assert refreshed_after_remove is not None
    assert refreshed_after_remove.relevant_files == [
        "src/engram/cli/task_cmds_query.py",
        "tests/test_task_cmds.py",
    ]


def test_task_files_validation_and_missing_task(tmp_db, project, monkeypatch) -> None:
    """task files commands reject missing tasks, blanks, and duplicate additions."""
    runner = make_runner_with_project(monkeypatch, project)
    task_item = Task.create(
        project_id=project.id,
        title="Task File Validation",
        relevant_files=["src/engram/cli/task_helpers.py"],
    )

    missing_result = runner.invoke(cli, ["task", "files", "list", "deadbeef"])
    assert missing_result.exit_code != 0
    assert "Task 'deadbeef' not found in this project." in missing_result.output

    blank_result = runner.invoke(
        cli,
        ["task", "files", "add", task_item.id, "--files", "src/a.py, ,src/b.py"],
    )
    assert blank_result.exit_code != 0
    assert "--files contains blank path entries at position(s): 2" in blank_result.output

    duplicate_add_result = runner.invoke(
        cli,
        ["task", "files", "add", task_item.id, "--files", "src/engram/cli/task_helpers.py"],
    )
    assert duplicate_add_result.exit_code != 0
    assert "already includes path(s): src/engram/cli/task_helpers.py" in duplicate_add_result.output

    missing_remove_result = runner.invoke(
        cli,
        ["task", "files", "remove", task_item.id, "--files", "src/missing.py"],
    )
    assert missing_remove_result.exit_code != 0
    assert "does not include path(s): src/missing.py" in missing_remove_result.output
