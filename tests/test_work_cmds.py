"""Tests for engram start and finish CLI commands, including safety checks and dynamic commit types."""

import pytest
from click.testing import CliRunner

from engram.cli import cli
from engram.models.phase import Phase
from engram.models.task import Task


class MockCompletedProcess:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def make_runner_with_project(monkeypatch, tmp_db, project) -> CliRunner:
    """Return a CliRunner with CWD patched to the project's repo path."""
    monkeypatch.setattr("engram.cli.get_current_project", lambda: project)
    return CliRunner()


@pytest.fixture
def mock_git(monkeypatch):
    """Fixture to mock git command subprocess executions."""
    commits = []
    calls = []
    status_stdout = ""
    branch_stdout = "main"

    def mock_run(args, **kwargs):
        mock_run.calls.append(args)
        # We handle specific mock scenarios
        if args == ["git", "status", "--porcelain"]:
            return MockCompletedProcess(0, stdout=mock_run.status_stdout)
        elif args == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return MockCompletedProcess(0, stdout=mock_run.branch_stdout)
        elif len(args) > 1 and args[1] == "show-ref":
            return MockCompletedProcess(0)  # Branch exists
        elif len(args) > 1 and args[1] == "commit":
            mock_run.commits.append(args)
            return MockCompletedProcess(0, stdout="[somebranch 12345] commit ok")
        elif len(args) > 1 and args[1] == "push":
            return MockCompletedProcess(0)
        return MockCompletedProcess(0)

    mock_run.commits = commits
    mock_run.calls = calls
    mock_run.status_stdout = status_stdout
    mock_run.branch_stdout = branch_stdout

    monkeypatch.setattr("subprocess.run", mock_run)
    return mock_run


# ---------------------------------------------------------------------------
# engram start tests
# ---------------------------------------------------------------------------


def test_start_success_when_clean(tmp_db, project, mock_git, monkeypatch):
    """engram start succeeds when working tree is clean."""
    Task.create(project_id=project.id, title="Task 1", phase="Phase 1", status="todo")

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])
    assert result.exit_code == 0
    assert "Started task" in result.output

    # Task should now be in-progress
    in_progress = [t for t in Task.list_by_project(project.id) if t.status == "in-progress"]
    assert len(in_progress) == 1
    assert in_progress[0].title == "Task 1"


def test_start_blocks_when_dirty_and_switching_branch(tmp_db, project, mock_git, monkeypatch):
    """engram start blocks when working tree is dirty and we need to switch branches."""
    # Create a task in Phase 1
    Task.create(project_id=project.id, title="Task 1", phase="Phase 1", status="todo")

    # Set mock git to be dirty and current branch to main
    mock_git.status_stdout = " M src/cli/work_cmds.py\n"
    mock_git.branch_stdout = "main"

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])

    # Should raise SystemExit(1)
    assert result.exit_code == 1
    assert "Error: Git working tree is dirty" in result.output
    assert "feat/phase-phase-1" in result.output

    # Task should still be in todo status
    tasks = Task.list_by_project(project.id)
    assert tasks[0].status == "todo"


def test_start_allows_when_dirty_on_same_branch(tmp_db, project, mock_git, monkeypatch):
    """engram start allows resuming/starting when dirty if we are already on the target branch."""
    Task.create(project_id=project.id, title="Task 1", phase="Phase 1", status="todo")

    # Set mock git to be dirty but already on the target branch
    mock_git.status_stdout = " M src/cli/work_cmds.py\n"
    mock_git.branch_stdout = "feat/phase-phase-1"

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])

    assert result.exit_code == 0
    assert "Started task" in result.output


def test_start_success_without_phase_clean(tmp_db, project, mock_git, monkeypatch) -> None:
    """engram start checks out feat/misc when starting a task with no phase and git is clean."""
    Task.create(project_id=project.id, title="Task No Phase", phase=None, status="todo")

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])
    assert result.exit_code == 0
    assert "Started task" in result.output

    # Check that it checks out the feat/misc branch
    in_progress = [t for t in Task.list_by_project(project.id) if t.status == "in-progress"]
    assert len(in_progress) == 1
    assert in_progress[0].title == "Task No Phase"


def test_start_blocks_without_phase_dirty(tmp_db, project, mock_git, monkeypatch) -> None:
    """engram start blocks when starting a task with no phase and git is dirty and not on feat/misc."""
    Task.create(project_id=project.id, title="Task No Phase", phase=None, status="todo")

    # Set mock git to be dirty and current branch to main
    mock_git.status_stdout = " M src/cli/work_cmds.py\n"
    mock_git.branch_stdout = "main"

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])

    # Should raise SystemExit(1)
    assert result.exit_code == 1
    assert "Error: Git working tree is dirty" in result.output
    assert "feat/misc" in result.output

    # Task should still be in todo status
    tasks = Task.list_by_project(project.id)
    assert tasks[0].status == "todo"


def test_start_allows_without_phase_dirty_on_same_branch(
    tmp_db, project, mock_git, monkeypatch
) -> None:
    """engram start allows starting a task with no phase when dirty if already on feat/misc."""
    Task.create(project_id=project.id, title="Task No Phase", phase=None, status="todo")

    # Set mock git to be dirty but already on the target branch (feat/misc)
    mock_git.status_stdout = " M src/cli/work_cmds.py\n"
    mock_git.branch_stdout = "feat/misc"

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])

    assert result.exit_code == 0
    assert "Started task" in result.output


# ---------------------------------------------------------------------------
# engram finish tests
# ---------------------------------------------------------------------------


def test_finish_with_explicit_type(tmp_db, project, mock_git, monkeypatch):
    """engram finish uses the type specified by the -t/--type flag."""
    # Create an in-progress task
    Task.create(
        project_id=project.id, title="Fix database WAL mode", phase="Phase 2", status="in-progress"
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["finish", "-t", "fix"])

    assert result.exit_code == 0
    assert "Finishing task:" in result.output
    assert len(mock_git.commits) == 1

    # Verify commit message has fix type
    commit_cmd = mock_git.commits[0]
    commit_msg = commit_cmd[commit_cmd.index("-m") + 1]
    assert commit_msg.startswith("fix(phase-2): Fix database WAL mode")


def test_finish_resolves_type_from_tags(tmp_db, project, mock_git, monkeypatch):
    """engram finish auto-resolves type from task tags (e.g. bug -> fix)."""
    # Create an in-progress task with a bug tag
    Task.create(
        project_id=project.id,
        title="Crash when listing empty projects",
        phase="Phase 3",
        status="in-progress",
        tags=["bug", "ui"],
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["finish"])

    assert result.exit_code == 0
    assert len(mock_git.commits) == 1

    # Verify commit message has resolved 'fix' type from 'bug' tag
    commit_cmd = mock_git.commits[0]
    commit_msg = commit_cmd[commit_cmd.index("-m") + 1]
    assert commit_msg.startswith("fix(phase-3): Crash when listing empty projects")


def test_finish_resolves_docs_type_from_tags(tmp_db, project, mock_git, monkeypatch):
    """engram finish auto-resolves type from task tags (e.g. documentation -> docs)."""
    Task.create(
        project_id=project.id,
        title="Update setup instructions",
        phase="Phase 3",
        status="in-progress",
        tags=["documentation"],
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["finish"])

    assert result.exit_code == 0
    assert len(mock_git.commits) == 1

    commit_cmd = mock_git.commits[0]
    commit_msg = commit_cmd[commit_cmd.index("-m") + 1]
    assert commit_msg.startswith("docs(phase-3): Update setup instructions")


def test_finish_falls_back_to_feat(tmp_db, project, mock_git, monkeypatch):
    """engram finish falls back to 'feat' type if no tags match any conventional types."""
    Task.create(
        project_id=project.id,
        title="Add settings page",
        phase="Phase 4",
        status="in-progress",
        tags=["some-other-tag"],
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["finish"])

    assert result.exit_code == 0
    assert len(mock_git.commits) == 1

    commit_cmd = mock_git.commits[0]
    commit_msg = commit_cmd[commit_cmd.index("-m") + 1]
    assert commit_msg.startswith("feat(phase-4): Add settings page")


def test_finish_rejects_invalid_type(tmp_db, project, mock_git, monkeypatch):
    """engram finish blocks and rejects invalid commit types."""
    Task.create(project_id=project.id, title="Refactor core db", status="in-progress")

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["finish", "-t", "invalidtype"])

    assert result.exit_code == 1
    assert "Error: Invalid commit type" in result.output
    assert len(mock_git.commits) == 0


def test_start_checkout_uses_first_class_phase_title(tmp_db, project, mock_git, monkeypatch):
    """engram start uses the first-class phase title if linked via phase_id."""
    phase = Phase.create(project_id=project.id, title="Phase Roadmap")
    Task.create(project_id=project.id, title="Task 1", phase_id=phase.id, status="todo")

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])
    assert result.exit_code == 0
    assert "Started task" in result.output

    # Verify that the checkout branch targets 'feat/phase-phase-roadmap'
    checkouts = [c for c in mock_git.calls if c[0:2] == ["git", "checkout"]]
    assert any("feat/phase-phase-roadmap" in cmd for cmd in checkouts)


def test_start_checkout_falls_back_to_legacy_phase_title(tmp_db, project, mock_git, monkeypatch):
    """engram start falls back to the legacy phase title if phase_id is missing."""
    Task.create(project_id=project.id, title="Task 1", phase="Phase Legacy", status="todo")

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])
    assert result.exit_code == 0
    assert "Started task" in result.output

    # Verify that the checkout branch targets 'feat/phase-phase-legacy'
    checkouts = [c for c in mock_git.calls if c[0:2] == ["git", "checkout"]]
    assert any("feat/phase-phase-legacy" in cmd for cmd in checkouts)


def test_start_checkout_handles_no_phase_gracefully(tmp_db, project, mock_git, monkeypatch):
    """engram start checks out 'feat/misc' if the task has no phase info."""
    Task.create(project_id=project.id, title="Task 1", phase=None, status="todo")

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])
    assert result.exit_code == 0
    assert "Started task" in result.output

    # Verify that the checkout branch targets 'feat/misc'
    checkouts = [c for c in mock_git.calls if c[0:2] == ["git", "checkout"]]
    assert any("feat/misc" in cmd for cmd in checkouts)


def test_finish_commit_uses_first_class_phase_title(tmp_db, project, mock_git, monkeypatch):
    """engram finish uses the first-class phase title if linked via phase_id."""
    phase = Phase.create(project_id=project.id, title="Phase Roadmap")
    Task.create(
        project_id=project.id,
        title="Refactor core db",
        phase_id=phase.id,
        status="in-progress",
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["finish", "-t", "feat"])

    assert result.exit_code == 0
    assert len(mock_git.commits) == 1
    commit_cmd = mock_git.commits[0]
    commit_msg = commit_cmd[commit_cmd.index("-m") + 1]
    assert commit_msg.startswith("feat(phase-roadmap): Refactor core db")


def test_finish_commit_falls_back_to_legacy_phase_title(tmp_db, project, mock_git, monkeypatch):
    """engram finish falls back to the legacy phase title if phase_id is missing."""
    Task.create(
        project_id=project.id,
        title="Refactor core db",
        phase="Phase Legacy",
        status="in-progress",
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["finish", "-t", "feat"])

    assert result.exit_code == 0
    assert len(mock_git.commits) == 1
    commit_cmd = mock_git.commits[0]
    commit_msg = commit_cmd[commit_cmd.index("-m") + 1]
    assert commit_msg.startswith("feat(phase-legacy): Refactor core db")


def test_finish_commit_handles_no_phase_gracefully(tmp_db, project, mock_git, monkeypatch):
    """engram finish uses 'misc' if the task has no phase info."""
    Task.create(
        project_id=project.id,
        title="Refactor core db",
        phase=None,
        status="in-progress",
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["finish", "-t", "feat"])

    assert result.exit_code == 0
    assert len(mock_git.commits) == 1
    commit_cmd = mock_git.commits[0]
    commit_msg = commit_cmd[commit_cmd.index("-m") + 1]
    assert commit_msg.startswith("feat(misc): Refactor core db")


def test_finish_phase_complete_with_phase_id(tmp_db, project, mock_git, monkeypatch):
    """engram finish detects Phase Complete! when all tasks in a first-class phase are done."""
    phase = Phase.create(project_id=project.id, title="Phase Roadmap")
    # Task 1 is already done, Task 2 is in-progress and will be finished
    Task.create(
        project_id=project.id,
        title="Task 1",
        phase_id=phase.id,
        status="done",
    )
    Task.create(
        project_id=project.id,
        title="Task 2",
        phase_id=phase.id,
        status="in-progress",
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["finish"])

    assert result.exit_code == 0
    assert "Phase Complete!" in result.output
    assert "All tasks in the current phase are done" in result.output


def test_finish_phase_complete_fallback_to_effective_title(tmp_db, project, mock_git, monkeypatch):
    """engram finish detects Phase Complete! using legacy fallback when phase_id is missing but titles match."""
    # Task 1 is done, Task 2 is in-progress and has no phase_id but matching legacy phase text
    Task.create(
        project_id=project.id,
        title="Task 1",
        phase="Phase Legacy",
        status="done",
    )
    Task.create(
        project_id=project.id,
        title="Task 2",
        phase="Phase Legacy",
        status="in-progress",
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["finish"])

    assert result.exit_code == 0
    assert "Phase Complete!" in result.output


def test_finish_phase_not_complete_same_phase_id_one_todo(tmp_db, project, mock_git, monkeypatch):
    """engram finish does not detect Phase Complete! if another task in the same phase_id is todo."""
    phase = Phase.create(project_id=project.id, title="Phase Roadmap")
    # Task 1 is in-progress, Task 2 is todo in the same phase
    Task.create(
        project_id=project.id,
        title="Task 1",
        phase_id=phase.id,
        status="in-progress",
    )
    Task.create(
        project_id=project.id,
        title="Task 2",
        phase_id=phase.id,
        status="todo",
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["finish"])

    assert result.exit_code == 0
    assert "Phase Complete!" not in result.output


def test_finish_phase_complete_with_other_phase_todo(tmp_db, project, mock_git, monkeypatch):
    """engram finish detects Phase Complete! when the current first-class phase is done, even if a different first-class phase has todo tasks."""
    phase_a = Phase.create(project_id=project.id, title="Phase A")
    phase_b = Phase.create(project_id=project.id, title="Phase B")

    # Task 1 in Phase A is in-progress
    Task.create(
        project_id=project.id,
        title="Task 1",
        phase_id=phase_a.id,
        status="in-progress",
    )
    # Task 2 in Phase B is todo
    Task.create(
        project_id=project.id,
        title="Task 2",
        phase_id=phase_b.id,
        status="todo",
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["finish"])

    assert result.exit_code == 0
    assert "Phase Complete!" in result.output


def test_start_prioritizes_active_phase_in_progress(tmp_db, project, mock_git, monkeypatch):
    """engram start prioritizes in-progress tasks from the active phase over other tasks."""
    phase_1 = Phase.create(project_id=project.id, title="Phase 1", status="active")
    phase_2 = Phase.create(project_id=project.id, title="Phase 2", status="planned")

    t_active_ip = Task.create(
        project_id=project.id,
        title="Active In-Progress",
        phase_id=phase_1.id,
        status="in-progress",
    )
    Task.create(
        project_id=project.id,
        title="Active Todo",
        phase_id=phase_1.id,
        status="todo",
    )
    Task.create(
        project_id=project.id,
        title="Other In-Progress",
        phase_id=phase_2.id,
        status="in-progress",
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])
    assert result.exit_code == 0
    assert "Resuming in-progress task:" in result.output
    assert t_active_ip.id in result.output


def test_start_prioritizes_active_phase_todo_over_other_in_progress(
    tmp_db, project, mock_git, monkeypatch
):
    """engram start prioritizes todo tasks from the active phase over in-progress tasks from other phases."""
    phase_1 = Phase.create(project_id=project.id, title="Phase 1", status="active")
    phase_2 = Phase.create(project_id=project.id, title="Phase 2", status="planned")

    t_active_todo = Task.create(
        project_id=project.id,
        title="Active Todo",
        phase_id=phase_1.id,
        status="todo",
    )
    Task.create(
        project_id=project.id,
        title="Other In-Progress",
        phase_id=phase_2.id,
        status="in-progress",
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])
    assert result.exit_code == 0
    assert "Started task:" in result.output
    assert t_active_todo.id in result.output


def test_start_prioritizes_legacy_in_progress_matching_active_phase(
    tmp_db, project, mock_git, monkeypatch
):
    """engram start treats legacy phase text as active-phase membership when phase_id is missing."""
    phase_1 = Phase.create(project_id=project.id, title="Phase 1", status="active")
    phase_2 = Phase.create(project_id=project.id, title="Phase 2", status="planned")

    Task.create(
        project_id=project.id,
        title="Other In-Progress",
        phase_id=phase_2.id,
        status="in-progress",
    )
    t_legacy_active = Task.create(
        project_id=project.id,
        title="Legacy Active In-Progress",
        phase=phase_1.title,
        status="in-progress",
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])
    assert result.exit_code == 0
    assert "Resuming in-progress task:" in result.output
    assert t_legacy_active.id in result.output


def test_start_prefers_unphased_project_task_before_other_phase_todo(
    tmp_db, project, mock_git, monkeypatch
):
    """When the active phase has no actionable work, start checks unphased work before other phases."""
    Phase.create(project_id=project.id, title="Phase 1", status="active")
    phase_2 = Phase.create(project_id=project.id, title="Phase 2", status="planned")

    Task.create(
        project_id=project.id,
        title="Other Phase Critical",
        phase_id=phase_2.id,
        status="todo",
        priority="critical",
    )
    t_unphased = Task.create(
        project_id=project.id,
        title="Unphased Project Task",
        status="todo",
        priority="medium",
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])
    assert result.exit_code == 0
    assert "Started task:" in result.output
    assert t_unphased.id in result.output


def test_start_falls_back_to_other_in_progress(tmp_db, project, mock_git, monkeypatch):
    """engram start falls back to other phase's in-progress tasks if no tasks in active phase."""
    _phase_1 = Phase.create(project_id=project.id, title="Phase 1", status="active")
    phase_2 = Phase.create(project_id=project.id, title="Phase 2", status="planned")

    t_other_ip = Task.create(
        project_id=project.id,
        title="Other In-Progress",
        phase_id=phase_2.id,
        status="in-progress",
    )
    Task.create(
        project_id=project.id,
        title="Other Todo",
        phase_id=phase_2.id,
        status="todo",
        priority="critical",
    )

    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["start"])
    assert result.exit_code == 0
    assert "Resuming in-progress task:" in result.output
    assert t_other_ip.id in result.output
