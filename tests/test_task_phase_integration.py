"""End-to-end CLI integration regression tests for task-phase behavior."""

import re

from click.testing import CliRunner

from engram.cli import cli
from engram.models.task import Task


def make_runner_with_project(monkeypatch, project) -> CliRunner:
    """Return a CliRunner with current-project resolution patched."""
    monkeypatch.setattr("engram.cli.get_current_project", lambda: project)
    return CliRunner()


def test_task_phase_integration_e2e(tmp_db, project, monkeypatch) -> None:
    """Validate full end-to-end integration flow between tasks and phases via CLI."""
    runner = make_runner_with_project(monkeypatch, project)

    # 1. Create Phase Alpha
    result = runner.invoke(
        cli,
        [
            "phase",
            "add",
            "Phase Alpha",
            "--description",
            "Alpha Phase Description",
        ],
    )
    assert result.exit_code == 0, result.output
    match_alpha = re.search(r"Phase created with ID:\s*([a-f0-9]{8})", result.output)
    assert match_alpha is not None
    phase_alpha_id = match_alpha.group(1)

    # 2. Create Phase Beta
    result = runner.invoke(
        cli,
        [
            "phase",
            "add",
            "Phase Beta",
            "--description",
            "Beta Phase Description",
        ],
    )
    assert result.exit_code == 0, result.output
    match_beta = re.search(r"Phase created with ID:\s*([a-f0-9]{8})", result.output)
    assert match_beta is not None
    phase_beta_id = match_beta.group(1)

    # 3. Add task by phase title
    result = runner.invoke(
        cli,
        [
            "task",
            "add",
            "Task by Title",
            "--phase",
            "Phase Alpha",
        ],
    )
    assert result.exit_code == 0, result.output
    match_task_title = re.search(r"Task created with ID:\s*([a-f0-9]{8})", result.output)
    assert match_task_title is not None
    task_title_id = match_task_title.group(1)

    # Verify task database state
    task_title_obj = Task.get(task_title_id)
    assert task_title_obj is not None
    assert task_title_obj.phase_id == phase_alpha_id
    assert task_title_obj.phase == "Phase Alpha"

    # 4. Add task by phase id
    result = runner.invoke(
        cli,
        [
            "task",
            "add",
            "Task by ID",
            "--phase",
            phase_beta_id,
        ],
    )
    assert result.exit_code == 0, result.output
    match_task_id = re.search(r"Task created with ID:\s*([a-f0-9]{8})", result.output)
    assert match_task_id is not None
    task_id_id = match_task_id.group(1)

    # Verify task database state
    task_id_obj = Task.get(task_id_id)
    assert task_id_obj is not None
    assert task_id_obj.phase_id == phase_beta_id
    assert task_id_obj.phase == "Phase Beta"

    # 5. List by phase
    # Filter by Phase Alpha (using title or ID)
    result = runner.invoke(cli, ["task", "list", "--phase", "phase alpha", "--status", "all"])
    assert result.exit_code == 0, result.output
    assert "Task by Title" in result.output
    assert "Task by ID" not in result.output

    # Filter by Phase Beta (using ID)
    result = runner.invoke(cli, ["task", "list", "--phase", phase_beta_id, "--status", "all"])
    assert result.exit_code == 0, result.output
    assert "Task by ID" in result.output
    assert "Task by Title" not in result.output

    # 6. Get shows effective phase title
    result = runner.invoke(cli, ["task", "get", task_title_id])
    assert result.exit_code == 0, result.output
    assert "Phase: Phase Alpha" in result.output

    result = runner.invoke(cli, ["task", "get", task_id_id])
    assert result.exit_code == 0, result.output
    assert "Phase: Phase Beta" in result.output

    # 7. Update task phase_id to another phase
    result = runner.invoke(
        cli,
        [
            "task",
            "update",
            task_title_id,
            "--field",
            "phase_id",
            "--value",
            phase_beta_id,
        ],
    )
    assert result.exit_code == 0, result.output
    task_title_obj_updated = Task.get(task_title_id)
    assert task_title_obj_updated is not None
    assert task_title_obj_updated.phase_id == phase_beta_id
    assert task_title_obj_updated.phase == "Phase Beta"

    # Verify task get displays the updated phase
    result = runner.invoke(cli, ["task", "get", task_title_id])
    assert result.exit_code == 0, result.output
    assert "Phase: Phase Beta" in result.output

    # 8. Clear task phase_id
    result = runner.invoke(
        cli,
        [
            "task",
            "update",
            task_title_id,
            "--field",
            "phase_id",
            "--value",
            "none",
        ],
    )
    assert result.exit_code == 0, result.output
    task_title_obj_cleared = Task.get(task_title_id)
    assert task_title_obj_cleared is not None
    assert task_title_obj_cleared.phase_id is None
    assert task_title_obj_cleared.phase is None

    # Verify task get displays Phase: N/A
    result = runner.invoke(cli, ["task", "get", task_title_id])
    assert result.exit_code == 0, result.output
    assert "Phase: N/A" in result.output

    # 9. Verify legacy --field phase tasks still work
    # Add a task with a freeform unmanaged phase that doesn't exist yet
    result = runner.invoke(
        cli,
        [
            "task",
            "add",
            "Legacy Task",
            "--phase",
            "Legacy Freeform Phase",
        ],
    )
    assert result.exit_code == 0, result.output
    match_legacy = re.search(r"Task created with ID:\s*([a-f0-9]{8})", result.output)
    assert match_legacy is not None
    legacy_task_id = match_legacy.group(1)

    # Immediately after creation (before another command startup migration runs),
    # the task in DB has phase_id = None and phase = "Legacy Freeform Phase".
    legacy_task_obj = Task.get(legacy_task_id)
    assert legacy_task_obj is not None
    assert legacy_task_obj.phase_id is None
    assert legacy_task_obj.phase == "Legacy Freeform Phase"

    # Now we execute a CLI get command. The click group startup runs init_db(),
    # which triggers the _backfill_legacy_phase_ids migration automatically!
    result = runner.invoke(cli, ["task", "get", legacy_task_id])
    assert result.exit_code == 0, result.output
    assert "Phase: Legacy Freeform Phase" in result.output

    # The task should now be automatically backfilled with a newly created phase ID!
    legacy_task_obj_after = Task.get(legacy_task_id)
    assert legacy_task_obj_after is not None
    assert legacy_task_obj_after.phase_id is not None
    assert legacy_task_obj_after.phase == "Legacy Freeform Phase"

    # Let's list the phases via CLI to ensure "Legacy Freeform Phase" is now a first-class phase!
    result = runner.invoke(cli, ["phase", "list"])
    assert result.exit_code == 0, result.output
    assert "Legacy Freeform Phase" in result.output

    # List tasks by the newly created phase should match the backfilled legacy task
    result = runner.invoke(
        cli, ["task", "list", "--phase", "Legacy Freeform Phase", "--status", "all"]
    )
    assert result.exit_code == 0, result.output
    assert "Legacy Task" in result.output

    # Once migration has created a first-class phase link, direct legacy phase updates
    # must not report success because phase_id controls the effective phase.
    result = runner.invoke(
        cli,
        [
            "task",
            "update",
            legacy_task_id,
            "--field",
            "phase",
            "--value",
            "Updated Legacy Phase",
        ],
    )
    assert result.exit_code != 0
    assert "Use --field phase_id" in result.output
    legacy_task_obj_updated = Task.get(legacy_task_id)
    assert legacy_task_obj_updated is not None
    assert legacy_task_obj_updated.phase_id == legacy_task_obj_after.phase_id
    assert legacy_task_obj_updated.phase == "Legacy Freeform Phase"
