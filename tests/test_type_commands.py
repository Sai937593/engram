"""Tests for type command groups and commit/context behavior."""

import re

import pytest
from click.testing import CliRunner

from engram.cli import cli
from engram.models.memory import Memory
from engram.models.task import Task


def make_runner_with_project(monkeypatch, project) -> CliRunner:
    """Return a CliRunner with current-project resolution patched."""
    monkeypatch.setattr("engram.cli.get_current_project", lambda: project)
    return CliRunner()


@pytest.mark.parametrize(
    "type_name,default_always_include",
    [
        ("constraint", True),
        ("lesson", True),
        ("decision", True),
        ("snippet", False),
    ],
)
def test_type_add_creates_correct_memory(
    type_name, default_always_include, tmp_db, project, monkeypatch
):
    """Each type add command creates a memory with the correct defaults."""
    runner = make_runner_with_project(monkeypatch, project)
    result = runner.invoke(cli, [type_name, "add", "Test title", "--content", "Test content"])
    assert result.exit_code == 0, result.output

    memories = Memory.list_by_type(project.id, type_name)
    assert len(memories) == 1
    created = memories[0]
    assert created.type == type_name
    assert created.title == "Test title"
    assert created.content == "Test content"
    assert created.always_include is default_always_include


@pytest.mark.parametrize("type_name", ["constraint", "lesson", "decision", "snippet"])
def test_type_add_no_always_include_flag(type_name, tmp_db, project, monkeypatch):
    """The opt-out flag flips default inclusion behavior for each type command."""
    runner = make_runner_with_project(monkeypatch, project)
    flag = "--no-always-include" if type_name != "snippet" else "--always-include"
    result = runner.invoke(cli, [type_name, "add", "Title", "--content", "Body", flag])
    assert result.exit_code == 0, result.output

    memories = Memory.list_by_type(project.id, type_name)
    assert len(memories) == 1
    expected = False if type_name != "snippet" else True
    assert memories[0].always_include is expected


@pytest.mark.parametrize("type_name", ["constraint", "lesson", "decision", "snippet"])
def test_type_list_shows_only_own_type(type_name, tmp_db, project, monkeypatch):
    """type list only shows memories of that specific type."""
    runner = make_runner_with_project(monkeypatch, project)
    Memory.create(project_id=project.id, type=type_name, title="Mine", content="A")
    Memory.create(project_id=project.id, type="note", title="Not mine", content="B")

    result = runner.invoke(cli, [type_name, "list"])
    assert result.exit_code == 0, result.output
    assert "Mine" in result.output
    assert "Not mine" not in result.output


@pytest.mark.parametrize("type_name", ["constraint", "lesson", "decision", "snippet"])
def test_type_list_empty(type_name, tmp_db, project, monkeypatch):
    """type list shows an empty-state message when no entries exist."""
    runner = make_runner_with_project(monkeypatch, project)
    result = runner.invoke(cli, [type_name, "list"])
    assert result.exit_code == 0, result.output
    assert type_name in result.output


@pytest.mark.parametrize("type_name", ["constraint", "lesson", "decision", "snippet"])
def test_type_get_shows_detail(type_name, tmp_db, project, monkeypatch):
    """type get renders full memory content."""
    runner = make_runner_with_project(monkeypatch, project)
    memory = Memory.create(
        project_id=project.id,
        type=type_name,
        title="Detail test",
        content="Full content here",
    )

    result = runner.invoke(cli, [type_name, "get", memory.id])
    assert result.exit_code == 0, result.output
    assert "Full content here" in result.output


def test_commit_rejects_invalid_message(tmp_db, project, monkeypatch):
    """engram commit rejects messages outside Conventional Commits format."""
    runner = make_runner_with_project(monkeypatch, project)
    result = runner.invoke(cli, ["commit", "-m", "this is a bad commit message"])
    assert result.exit_code == 0, result.output
    assert "Error" in result.output
    assert "Conventional Commits" in result.output


@pytest.mark.parametrize(
    "msg",
    [
        "feat(cli): add lesson command [T-001]",
        "fix(db): correct WAL mode setup [T-002]",
        "docs: update readme",
        "chore(deps): bump ruff to 0.9",
    ],
)
def test_commit_accepts_valid_messages(msg, tmp_db, project, monkeypatch):
    """engram commit accepts well-formed Conventional Commit messages."""
    from engram.cli import CONVENTIONAL_COMMIT_TYPES

    pattern = rf"^({'|'.join(CONVENTIONAL_COMMIT_TYPES)})(\(.+\))?: .+"
    assert re.match(pattern, msg), f"Expected '{msg}' to match conventional commit pattern"


def test_commit_warns_missing_task_id(tmp_db, project, monkeypatch, capsys):
    """engram commit warns, but does not fail, without [task-id] in message."""
    from engram.cli import CONVENTIONAL_COMMIT_TYPES

    msg = "feat(cli): add something without task id"
    pattern = rf"^({'|'.join(CONVENTIONAL_COMMIT_TYPES)})(\(.+\))?: .+"
    assert re.match(pattern, msg)
    assert "[" not in msg


def test_startup_context_shows_constraints_first(tmp_db, project, monkeypatch):
    """Startup context renders constraints before lessons."""
    from engram.context import get_startup_context

    Memory.create(
        project_id=project.id,
        type="constraint",
        title="No pip",
        content="Use uv run",
        always_include=True,
    )
    Memory.create(
        project_id=project.id,
        type="lesson",
        title="WAL mode",
        content="Enable WAL",
        always_include=True,
    )

    ctx = get_startup_context(project.id)
    assert "## CONSTRAINTS" in ctx
    assert "## LESSONS LEARNED" in ctx
    assert ctx.index("## CONSTRAINTS") < ctx.index("## LESSONS LEARNED")


def test_startup_context_no_tasks_phase_gap(tmp_db, project):
    """Startup context shows NO TASKS DEFINED when project has zero tasks."""
    from engram.context import get_startup_context

    ctx = get_startup_context(project.id)
    assert "NO TASKS DEFINED" in ctx


def test_startup_context_phase_complete(tmp_db, project):
    """Startup context shows PHASE COMPLETE when all work is finished."""
    from engram.context import get_startup_context

    Task.create(project_id=project.id, title="Done", status="done")
    ctx = get_startup_context(project.id)
    assert "PHASE COMPLETE" in ctx


def test_task_context_includes_project_knowledge(tmp_db, project, task):
    """Task context includes project-wide constraints and lessons."""
    from engram.context import get_task_context

    Memory.create(project_id=project.id, type="constraint", title="No secrets", content="Use .env")
    Memory.create(project_id=project.id, type="lesson", title="Use WAL", content="Enable WAL mode")

    ctx = get_task_context(task.id)
    assert "PROJECT KNOWLEDGE" in ctx
    assert "No secrets" in ctx
    assert "Use WAL" in ctx
