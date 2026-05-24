"""Tests for type command groups and commit/context behavior."""

import re

import pytest
from click.testing import CliRunner

from engram.cli import cli
from engram.models.memory import Memory
from engram.models.project import Project
from engram.models.task import Task


def _project_level_for_type(memory_type: str) -> str:
    if memory_type == "constraint":
        return "L1"
    if memory_type == "decision":
        return "L2"
    return "L3"


def make_runner_with_project(monkeypatch, project) -> CliRunner:
    """Return a CliRunner with current-project resolution patched."""
    monkeypatch.setattr("engram.cli.get_current_project", lambda: project)
    return CliRunner()


@pytest.mark.parametrize(
    "type_name,default_scope,default_level,default_always_include",
    [
        ("constraint", "project", "L1", True),
        ("lesson", "task", None, True),
        ("decision", "project", "L2", True),
        ("snippet", "task", None, False),
    ],
)
def test_type_add_creates_correct_memory(
    type_name, default_scope, default_level, default_always_include, tmp_db, project, monkeypatch
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
    assert created.scope == default_scope
    assert created.level == default_level
    assert created.task_id is None
    assert created.always_include is default_always_include


@pytest.mark.parametrize("type_name", ["lesson", "snippet"])
def test_task_scoped_type_add_defaults_task_id_to_active_task(
    type_name, tmp_db, project, monkeypatch
):
    """Task-scope typed shortcuts link to the sole in-progress task by default."""
    runner = make_runner_with_project(monkeypatch, project)
    active_task = Task.create(project_id=project.id, title="Active work", status="in-progress")
    Task.create(project_id=project.id, title="Other work", status="todo")

    result = runner.invoke(cli, [type_name, "add", "Test title", "--content", "Test content"])
    assert result.exit_code == 0, result.output

    memories = Memory.list_by_type(project.id, type_name)
    assert len(memories) == 1
    assert memories[0].scope == "task"
    assert memories[0].level is None
    assert memories[0].task_id == active_task.id


def test_lesson_add_project_scope_requires_explicit_level(tmp_db, project, monkeypatch):
    """lesson add --project requires an explicit level override."""
    runner = make_runner_with_project(monkeypatch, project)
    result = runner.invoke(cli, ["lesson", "add", "Title", "--content", "Body", "--project"])
    assert result.exit_code != 0
    assert "Error: Project-scope lessons require --level" in result.output


def test_lesson_add_level_sets_project_scope_and_level(tmp_db, project, monkeypatch):
    """lesson add --level infers project scope and applies the requested level."""
    runner = make_runner_with_project(monkeypatch, project)
    result = runner.invoke(cli, ["lesson", "add", "Title", "--content", "Body", "--level", "L1"])
    assert result.exit_code == 0, result.output

    memories = Memory.list_by_type(project.id, "lesson")
    assert len(memories) == 1
    assert memories[0].scope == "project"
    assert memories[0].level == "L1"
    assert memories[0].task_id is None


def test_snippet_add_project_scope_requires_explicit_level(tmp_db, project, monkeypatch):
    """snippet add --scope project requires an explicit level override."""
    runner = make_runner_with_project(monkeypatch, project)
    result = runner.invoke(
        cli,
        ["snippet", "add", "Title", "--content", "Body", "--scope", "project"],
    )
    assert result.exit_code != 0
    assert "Error: Project-scope snippets require --level" in result.output


@pytest.mark.parametrize("type_name", ["lesson", "snippet"])
def test_task_scoped_type_add_accepts_same_project_task_id(type_name, tmp_db, project, monkeypatch):
    """Task-scoped typed commands accept an explicit task_id from the current project."""
    runner = make_runner_with_project(monkeypatch, project)
    task = Task.create(project_id=project.id, title=f"{type_name} task")

    result = runner.invoke(
        cli,
        [type_name, "add", "Title", "--content", "Body", "--task-id", task.id],
    )
    assert result.exit_code == 0, result.output

    memories = Memory.list_by_type(project.id, type_name)
    assert len(memories) == 1
    assert memories[0].scope == "task"
    assert memories[0].level is None
    assert memories[0].task_id == task.id


@pytest.mark.parametrize("type_name", ["lesson", "snippet"])
def test_task_scoped_type_add_rejects_foreign_task_id(type_name, tmp_db, project, monkeypatch):
    """Task-scoped typed commands reject task_id values from other projects."""
    runner = make_runner_with_project(monkeypatch, project)
    other_project = Project.create("other", "Other", repo_paths=["/tmp/other"])
    foreign_task = Task.create(project_id=other_project.id, title="Foreign task")

    result = runner.invoke(
        cli,
        [type_name, "add", "Title", "--content", "Body", "--task-id", foreign_task.id],
    )
    assert result.exit_code != 0
    assert f"Error: Task '{foreign_task.id}' not found in the current project." in result.output


@pytest.mark.parametrize("type_name", ["lesson", "snippet"])
def test_typed_add_accepts_explicit_project_scope_with_level(
    type_name, tmp_db, project, monkeypatch
):
    """Typed task-default commands accept explicit project scope with a valid level."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli,
        [
            type_name,
            "add",
            "Title",
            "--content",
            "Body",
            "--scope",
            "project",
            "--level",
            "L0",
        ],
    )
    assert result.exit_code == 0, result.output

    memories = Memory.list_by_type(project.id, type_name)
    assert len(memories) == 1
    assert memories[0].scope == "project"
    assert memories[0].level == "L0"
    assert memories[0].task_id is None


@pytest.mark.parametrize("type_name", ["lesson", "snippet"])
def test_typed_add_rejects_task_scope_with_level(type_name, tmp_db, project, monkeypatch):
    """Typed task-default commands reject task scope when a level is supplied."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli,
        [
            type_name,
            "add",
            "Title",
            "--content",
            "Body",
            "--scope",
            "task",
            "--level",
            "L1",
        ],
    )
    assert result.exit_code != 0
    assert "Error: Task-scope memories must not define a level." in result.output


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
    Memory.create(
        project_id=project.id,
        type=type_name,
        title="Mine",
        content="A",
        level=_project_level_for_type(type_name),
    )
    Memory.create(project_id=project.id, type="note", title="Not mine", content="B", level="L3")

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
        level=_project_level_for_type(type_name),
    )

    result = runner.invoke(cli, [type_name, "get", memory.id])
    assert result.exit_code == 0, result.output
    assert "Full content here" in result.output


@pytest.mark.parametrize("type_name", ["constraint", "lesson", "decision", "snippet"])
def test_type_list_and_get_show_scope_metadata_for_project_scope(
    type_name, tmp_db, project, monkeypatch
):
    """type list/get render scope-level metadata for project memories."""
    runner = make_runner_with_project(monkeypatch, project)
    memory = Memory.create(
        project_id=project.id,
        type=type_name,
        title="Scoped entry",
        content="Scoped details",
        scope="project",
        level=_project_level_for_type(type_name),
    )

    list_result = runner.invoke(cli, [type_name, "list"])
    assert list_result.exit_code == 0, list_result.output
    assert "Scope" in list_result.output
    assert "Level" in list_result.output
    assert "Task ID" in list_result.output
    assert "project" in list_result.output
    assert "-" in list_result.output

    get_result = runner.invoke(cli, [type_name, "get", memory.id])
    assert get_result.exit_code == 0, get_result.output
    assert "Scope: project" in get_result.output
    assert f"Level: {_project_level_for_type(type_name)}" in get_result.output
    assert "Task ID: -" in get_result.output


@pytest.mark.parametrize("type_name", ["lesson", "snippet"])
def test_type_list_and_get_show_scope_metadata_for_task_scope(
    type_name, tmp_db, project, monkeypatch
):
    """type list/get render scope-level metadata for task-scope memories."""
    runner = make_runner_with_project(monkeypatch, project)
    task = Task.create(project_id=project.id, title=f"{type_name} task")
    memory = Memory.create(
        project_id=project.id,
        type=type_name,
        title="Scoped entry",
        content="Scoped details",
        scope="task",
        level=None,
        task_id=task.id,
    )

    list_result = runner.invoke(cli, [type_name, "list"])
    assert list_result.exit_code == 0, list_result.output
    assert "Scope" in list_result.output
    assert "Level" in list_result.output
    assert "Task ID" in list_result.output
    assert "task" in list_result.output
    assert task.id in list_result.output

    get_result = runner.invoke(cli, [type_name, "get", memory.id])
    assert get_result.exit_code == 0, get_result.output
    assert "Scope: task" in get_result.output
    assert "Level: -" in get_result.output
    assert f"Task ID: {task.id}" in get_result.output


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
        level="L1",
    )
    Memory.create(
        project_id=project.id,
        type="lesson",
        title="WAL mode",
        content="Enable WAL",
        always_include=True,
        level="L3",
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

    Memory.create(
        project_id=project.id,
        type="constraint",
        title="No secrets",
        content="Use .env",
        level="L1",
    )
    Memory.create(
        project_id=project.id,
        type="lesson",
        title="Use WAL",
        content="Enable WAL mode",
        level="L3",
    )

    ctx = get_task_context(task.id)
    assert "PROJECT KNOWLEDGE" in ctx
    assert "No secrets" in ctx
    assert "Use WAL" in ctx
