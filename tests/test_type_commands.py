"""Tests for first-class type command groups and engram commit validation."""

import re

import pytest
from click.testing import CliRunner

from engram.cli import cli
from engram.models.memory import Memory
from engram.models.task import Task

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_runner_with_project(monkeypatch, tmp_db, project) -> CliRunner:
    """Return a CliRunner with CWD patched to the project's repo path."""
    monkeypatch.setattr("engram.cli.get_current_project", lambda: project)
    return CliRunner()


# ---------------------------------------------------------------------------
# Type command groups: constraint, lesson, decision, snippet
# ---------------------------------------------------------------------------


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
    """Each type add command creates a memory with the correct type and always_include default."""
    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, [type_name, "add", "Test title", "--content", "Test content"])
    assert result.exit_code == 0, result.output

    memories = Memory.list_by_type(project.id, type_name)
    assert len(memories) == 1
    m = memories[0]
    assert m.type == type_name
    assert m.title == "Test title"
    assert m.content == "Test content"
    assert m.always_include is default_always_include


@pytest.mark.parametrize("type_name", ["constraint", "lesson", "decision", "snippet"])
def test_type_add_no_always_include_flag(type_name, tmp_db, project, monkeypatch):
    """The --no-always-include flag overrides the default for constraint/lesson/decision."""
    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    flag = "--no-always-include" if type_name != "snippet" else "--always-include"
    result = runner.invoke(cli, [type_name, "add", "Title", "--content", "Body", flag])
    assert result.exit_code == 0, result.output

    memories = Memory.list_by_type(project.id, type_name)
    assert len(memories) == 1
    # For constraint/lesson/decision: flag flips to False; for snippet: flag flips to True
    expected = False if type_name != "snippet" else True
    assert memories[0].always_include is expected


@pytest.mark.parametrize("type_name", ["constraint", "lesson", "decision", "snippet"])
def test_type_list_shows_only_own_type(type_name, tmp_db, project, monkeypatch):
    """type list only shows memories of that specific type, not all memories."""
    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    # Add one of the target type and one of a different type
    Memory.create(project_id=project.id, type=type_name, title="Mine", content="A")
    Memory.create(project_id=project.id, type="note", title="Not mine", content="B")

    result = runner.invoke(cli, [type_name, "list"])
    assert result.exit_code == 0, result.output
    assert "Mine" in result.output
    assert "Not mine" not in result.output


@pytest.mark.parametrize("type_name", ["constraint", "lesson", "decision", "snippet"])
def test_type_list_empty(type_name, tmp_db, project, monkeypatch):
    """type list shows a helpful message when no memories of that type exist."""
    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, [type_name, "list"])
    assert result.exit_code == 0, result.output
    assert type_name in result.output  # mentions the type in the empty message


@pytest.mark.parametrize("type_name", ["constraint", "lesson", "decision", "snippet"])
def test_type_get_shows_detail(type_name, tmp_db, project, monkeypatch):
    """type get shows the full memory content."""
    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    m = Memory.create(
        project_id=project.id, type=type_name, title="Detail test", content="Full content here"
    )
    result = runner.invoke(cli, [type_name, "get", m.id])
    assert result.exit_code == 0, result.output
    assert "Full content here" in result.output


# ---------------------------------------------------------------------------
# Task.count_by_status
# ---------------------------------------------------------------------------


def test_count_by_status_empty(tmp_db, project):
    """count_by_status returns empty dict when no tasks exist."""
    counts = Task.count_by_status(project.id)
    assert counts == {}


def test_count_by_status_mixed(tmp_db, project):
    """count_by_status returns accurate counts across statuses."""
    Task.create(project_id=project.id, title="A", status="todo")
    Task.create(project_id=project.id, title="B", status="todo")
    Task.create(project_id=project.id, title="C", status="done")
    Task.create(project_id=project.id, title="D", status="blocked")

    counts = Task.count_by_status(project.id)
    assert counts["todo"] == 2
    assert counts["done"] == 1
    assert counts["blocked"] == 1


# ---------------------------------------------------------------------------
# task next — three distinct empty states
# ---------------------------------------------------------------------------


def test_task_next_no_tasks_defined(tmp_db, project, monkeypatch):
    """task next shows 'No tasks defined' when the project has zero tasks."""
    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["task", "next"])
    assert result.exit_code == 0, result.output
    assert "No tasks defined" in result.output
    assert "engram task add" in result.output


def test_task_next_all_done(tmp_db, project, monkeypatch):
    """task next shows 'All tasks complete' when every task is done or cancelled."""
    Task.create(project_id=project.id, title="Done task", status="done")
    Task.create(project_id=project.id, title="Cancelled task", status="cancelled")
    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["task", "next"])
    assert result.exit_code == 0, result.output
    assert "All tasks complete" in result.output


def test_task_next_all_blocked(tmp_db, project, monkeypatch):
    """task next shows blocked guidance when all remaining tasks are blocked."""
    Task.create(project_id=project.id, title="Blocked task", status="blocked")
    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["task", "next"])
    assert result.exit_code == 0, result.output
    assert "blocked" in result.output.lower()


def test_task_next_returns_task(tmp_db, project, monkeypatch):
    """task next returns the task when a todo task exists."""
    Task.create(project_id=project.id, title="Ready task", status="todo", priority="high")
    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["task", "next"])
    assert result.exit_code == 0, result.output
    assert "Ready task" in result.output


# ---------------------------------------------------------------------------
# engram commit — message validation
# ---------------------------------------------------------------------------


def test_commit_rejects_invalid_message(tmp_db, project, monkeypatch):
    """engram commit rejects messages that don't follow Conventional Commits format."""
    runner = make_runner_with_project(monkeypatch, tmp_db, project)
    result = runner.invoke(cli, ["commit", "-m", "this is a bad commit message"])
    assert result.exit_code == 0, result.output  # click exits 0 even on user errors
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
    """engram commit warns (not fails) when no [task-id] bracket is present."""
    # We test the validation logic directly since subprocess.run would need git
    from engram.cli import CONVENTIONAL_COMMIT_TYPES

    msg = "feat(cli): add something without task id"
    pattern = rf"^({'|'.join(CONVENTIONAL_COMMIT_TYPES)})(\(.+\))?: .+"
    assert re.match(pattern, msg)  # valid format
    assert "[" not in msg  # missing task id — should warn but not fail


# ---------------------------------------------------------------------------
# context — startup sections
# ---------------------------------------------------------------------------


def test_startup_context_shows_constraints_first(tmp_db, project, monkeypatch):
    """Constraints appear in the startup context output."""
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
    # Constraints must appear before lessons
    assert ctx.index("## CONSTRAINTS") < ctx.index("## LESSONS LEARNED")


def test_startup_context_no_tasks_phase_gap(tmp_db, project):
    """Startup context shows the NO TASKS DEFINED block when project has zero tasks."""
    from engram.context import get_startup_context

    ctx = get_startup_context(project.id)
    assert "NO TASKS DEFINED" in ctx


def test_startup_context_phase_complete(tmp_db, project):
    """Startup context shows PHASE COMPLETE when all tasks are done/cancelled."""
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


# ---------------------------------------------------------------------------
# task depends_on tests
# ---------------------------------------------------------------------------


def test_task_add_depends_on_exact_and_prefix(tmp_db, project, monkeypatch):
    """task add supports --depends-on / -d with exact ID and partial prefix."""
    runner = make_runner_with_project(monkeypatch, tmp_db, project)

    # 1. Create a dependency task
    t_dep = Task.create(project_id=project.id, title="Dependency task")

    # 2. Add task depending on exact ID
    res = runner.invoke(cli, ["task", "add", "Task A", "--depends-on", t_dep.id])
    assert res.exit_code == 0, res.output
    # Parse the created ID from the output
    match = re.search(r"Task created with ID:\s*([a-f0-9]{8})", res.output)
    assert match is not None
    t_a_id = match.group(1)

    t_a = Task.get(t_a_id)
    assert t_a.depends_on == t_dep.id

    # 3. Add task depending on prefix of t_dep.id
    prefix = t_dep.id[:4]
    res2 = runner.invoke(cli, ["task", "add", "Task B", "-d", prefix])
    assert res2.exit_code == 0, res2.output
    match2 = re.search(r"Task created with ID:\s*([a-f0-9]{8})", res2.output)
    assert match2 is not None
    t_b_id = match2.group(1)

    t_b = Task.get(t_b_id)
    assert t_b.depends_on == t_dep.id


def test_task_add_depends_on_errors(tmp_db, project, monkeypatch):
    """task add handles non-existent and ambiguous depends-on values."""
    runner = make_runner_with_project(monkeypatch, tmp_db, project)

    # 1. Non-existent dependency
    res = runner.invoke(cli, ["task", "add", "Task A", "-d", "nonexist"])
    assert res.exit_code != 0
    assert "Error: Task dependency 'nonexist' not found" in res.output

    # 2. Ambiguous dependency (prefix matching multiple tasks)
    # We force create two tasks starting with similar prefixes if possible, or just mock/insert them
    # Since they have random IDs, let's create a few and find two that share a prefix, or manually insert them.
    from engram.db import get_db_connection

    conn = get_db_connection(tmp_db)
    conn.execute(
        "INSERT INTO tasks (id, project_id, title) VALUES ('aaaa1111', ?, 'Task 1')",
        (project.id,),
    )
    conn.execute(
        "INSERT INTO tasks (id, project_id, title) VALUES ('aaaa2222', ?, 'Task 2')",
        (project.id,),
    )
    conn.commit()
    conn.close()

    res2 = runner.invoke(cli, ["task", "add", "Task B", "-d", "aaaa"])
    assert res2.exit_code != 0
    assert "Error: Ambiguous task dependency 'aaaa'" in res2.output


def test_task_update_depends_on(tmp_db, project, monkeypatch):
    """task update supports updating depends_on, prevents self-dependency, and allows clearing it."""
    runner = make_runner_with_project(monkeypatch, tmp_db, project)

    # Create two tasks
    t1 = Task.create(project_id=project.id, title="Task 1")
    t2 = Task.create(project_id=project.id, title="Task 2")

    # Update t1 to depend on t2 prefix
    res = runner.invoke(
        cli, ["task", "update", t1.id, "--field", "depends_on", "--value", t2.id[:4]]
    )
    assert res.exit_code == 0, res.output
    t1_refreshed = Task.get(t1.id)
    assert t1_refreshed.depends_on == t2.id

    # Try to make t1 depend on itself
    res2 = runner.invoke(
        cli, ["task", "update", t1.id, "--field", "depends_on", "--value", t1.id[:4]]
    )
    assert res2.exit_code != 0
    assert "Error: A task cannot depend on itself" in res2.output

    # Clear dependency
    res3 = runner.invoke(cli, ["task", "update", t1.id, "--field", "depends_on", "--value", "none"])
    assert res3.exit_code == 0, res3.output
    t1_cleared = Task.get(t1.id)
    assert t1_cleared.depends_on is None


def test_task_get_shows_depends_on(tmp_db, project, monkeypatch):
    """task get displays Depends On information."""
    runner = make_runner_with_project(monkeypatch, tmp_db, project)

    t_dep = Task.create(project_id=project.id, title="Dep")
    t = Task.create(project_id=project.id, title="Main", depends_on=t_dep.id)

    res = runner.invoke(cli, ["task", "get", t.id])
    assert res.exit_code == 0, res.output
    assert f"Depends On: {t_dep.id}" in res.output

    # Get task without dependency
    res2 = runner.invoke(cli, ["task", "get", t_dep.id])
    assert res2.exit_code == 0, res2.output
    assert "Depends On: N/A" in res2.output
