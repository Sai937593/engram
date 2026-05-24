"""CLI tests for generic memory command scope/level/task_id behavior."""

from click.testing import CliRunner

from engram.cli import cli
from engram.models.memory import Memory
from engram.models.project import Project
from engram.models.task import Task


def make_runner_with_project(monkeypatch, project) -> CliRunner:
    """Return a CliRunner with current-project resolution patched."""
    monkeypatch.setattr("engram.cli.get_current_project", lambda: project)
    return CliRunner()


def test_memory_add_project_scope_requires_level(tmp_db, project, monkeypatch) -> None:
    """memory add rejects explicit project scope when level is omitted."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli, ["memory", "add", "Rule", "--content", "Use uv", "--scope", "project"]
    )

    assert result.exit_code != 0
    assert "Error: Project-scope memories require a valid level" in result.output
    assert "Traceback" not in result.output


def test_memory_add_rejects_task_scope_with_level(tmp_db, project, monkeypatch) -> None:
    """memory add enforces that task-scope memories cannot define a level."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli,
        [
            "memory",
            "add",
            "Task note",
            "--content",
            "body",
            "--scope",
            "task",
            "--level",
            "L1",
        ],
    )

    assert result.exit_code != 0
    assert "Error: Task-scope memories must not define a level" in result.output


def test_memory_add_rejects_invalid_scope_value(tmp_db, project, monkeypatch) -> None:
    """memory add rejects unsupported scope values with a clear error."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli,
        [
            "memory",
            "add",
            "Rule",
            "--content",
            "Use uv",
            "--scope",
            "phase",
        ],
    )

    assert result.exit_code != 0
    assert "Error: Invalid memory scope 'phase'" in result.output
    assert "Traceback" not in result.output


def test_memory_add_rejects_invalid_level_value(tmp_db, project, monkeypatch) -> None:
    """memory add rejects unsupported project level values with a clear error."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli,
        [
            "memory",
            "add",
            "Rule",
            "--content",
            "Use uv",
            "--scope",
            "project",
            "--level",
            "L9",
        ],
    )

    assert result.exit_code != 0
    assert "Error: Invalid memory level 'L9'" in result.output
    assert "Traceback" not in result.output


def test_memory_add_uses_backward_compatible_defaults_when_optional_flags_omitted(
    tmp_db, project, monkeypatch
) -> None:
    """memory add keeps legacy defaults when scope/level/task_id are not provided."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(
        cli,
        [
            "memory",
            "add",
            "Rule",
            "--content",
            "Use uv",
        ],
    )

    assert result.exit_code == 0, result.output
    created = Memory.list_by_project(project.id)[0]
    assert created.scope == "project"
    assert created.level == "L3"
    assert created.task_id is None


def test_memory_add_accepts_task_scope_with_same_project_task(tmp_db, project, monkeypatch) -> None:
    """memory add accepts task scope when task_id belongs to current project."""
    runner = make_runner_with_project(monkeypatch, project)
    task = Task.create(project_id=project.id, title="Implement feature")

    result = runner.invoke(
        cli,
        [
            "memory",
            "add",
            "Task lesson",
            "--content",
            "Reusable lesson",
            "--scope",
            "task",
            "--task-id",
            task.id,
        ],
    )

    assert result.exit_code == 0, result.output
    created = Memory.list_by_project(project.id)[0]
    assert created.scope == "task"
    assert created.level is None
    assert created.task_id == task.id


def test_memory_add_rejects_task_id_outside_current_project(tmp_db, project, monkeypatch) -> None:
    """memory add rejects task_id values that resolve to another project."""
    runner = make_runner_with_project(monkeypatch, project)
    other_project = Project.create("other", "Other", repo_paths=["/tmp/other"])
    foreign_task = Task.create(project_id=other_project.id, title="Foreign task")

    result = runner.invoke(
        cli,
        [
            "memory",
            "add",
            "Task lesson",
            "--content",
            "Reusable lesson",
            "--scope",
            "task",
            "--task-id",
            foreign_task.id,
        ],
    )

    assert result.exit_code != 0
    assert f"Error: Task '{foreign_task.id}' not found in the current project." in result.output
    assert "Traceback" not in result.output


def test_memory_update_scope_to_task_clears_level(tmp_db, project, monkeypatch) -> None:
    """memory update scope=task auto-clears a previously project-only level."""
    runner = make_runner_with_project(monkeypatch, project)
    memory = Memory.create(
        project_id=project.id,
        type="decision",
        title="Architecture",
        content="Use sqlite",
        scope="project",
        level="L2",
    )

    result = runner.invoke(
        cli, ["memory", "update", memory.id, "--field", "scope", "--value", "task"]
    )

    assert result.exit_code == 0, result.output
    refreshed = Memory.get(memory.id)
    assert refreshed is not None
    assert refreshed.scope == "task"
    assert refreshed.level is None


def test_memory_update_scope_to_project_assigns_default_level(tmp_db, project, monkeypatch) -> None:
    """memory update scope=project fills a valid default level when converting from task."""
    runner = make_runner_with_project(monkeypatch, project)
    memory = Memory.create(
        project_id=project.id,
        type="note",
        title="Local note",
        content="Body",
        scope="task",
        level=None,
    )

    result = runner.invoke(
        cli,
        ["memory", "update", memory.id, "--field", "scope", "--value", "project"],
    )

    assert result.exit_code == 0, result.output
    refreshed = Memory.get(memory.id)
    assert refreshed is not None
    assert refreshed.scope == "project"
    assert refreshed.level == "L3"


def test_memory_update_task_id_requires_current_project_task(tmp_db, project, monkeypatch) -> None:
    """memory update task_id validates that referenced tasks belong to project."""
    runner = make_runner_with_project(monkeypatch, project)
    memory = Memory.create(
        project_id=project.id,
        type="note",
        title="Local note",
        content="Body",
        scope="project",
        level="L3",
    )

    result = runner.invoke(
        cli, ["memory", "update", memory.id, "--field", "task_id", "--value", "missing123"]
    )

    assert result.exit_code != 0
    assert "Error: Task 'missing123' not found in the current project." in result.output


def test_memory_update_rejects_invalid_scope_value(tmp_db, project, monkeypatch) -> None:
    """memory update rejects unsupported scope values with a clear error."""
    runner = make_runner_with_project(monkeypatch, project)
    memory = Memory.create(
        project_id=project.id,
        type="note",
        title="Local note",
        content="Body",
        scope="project",
        level="L3",
    )

    result = runner.invoke(
        cli, ["memory", "update", memory.id, "--field", "scope", "--value", "phase"]
    )

    assert result.exit_code != 0
    assert "Error: Invalid memory scope 'phase'" in result.output
    assert "Traceback" not in result.output


def test_memory_update_rejects_invalid_level_value(tmp_db, project, monkeypatch) -> None:
    """memory update rejects unsupported level values with a clear error."""
    runner = make_runner_with_project(monkeypatch, project)
    memory = Memory.create(
        project_id=project.id,
        type="note",
        title="Local note",
        content="Body",
        scope="project",
        level="L3",
    )

    result = runner.invoke(
        cli, ["memory", "update", memory.id, "--field", "level", "--value", "L9"]
    )

    assert result.exit_code != 0
    assert "Error: Invalid memory level 'L9'" in result.output
    assert "Traceback" not in result.output


def test_memory_list_and_get_show_scope_fields(tmp_db, project, monkeypatch) -> None:
    """memory list/get include scope, level, and task_id in rendered output."""
    runner = make_runner_with_project(monkeypatch, project)
    task = Task.create(project_id=project.id, title="Task A")
    memory = Memory.create(
        project_id=project.id,
        type="lesson",
        title="Scoped memory",
        content="Details",
        scope="task",
        level=None,
        task_id=task.id,
    )

    list_result = runner.invoke(cli, ["memory", "list"])
    assert list_result.exit_code == 0, list_result.output
    assert "Scope" in list_result.output
    assert "Level" in list_result.output
    assert "Task ID" in list_result.output
    assert "task" in list_result.output
    assert task.id in list_result.output

    get_result = runner.invoke(cli, ["memory", "get", memory.id])
    assert get_result.exit_code == 0, get_result.output
    assert "Scope: task" in get_result.output
    assert "Level: -" in get_result.output
    assert f"Task ID: {task.id}" in get_result.output


def test_memory_related_to_task_missing_error(tmp_db, project, monkeypatch) -> None:
    """memory related-to-task rejects completely missing task ID with clear error."""
    runner = make_runner_with_project(monkeypatch, project)

    result = runner.invoke(cli, ["memory", "related-to-task", "missing1"])

    assert result.exit_code != 0
    assert "Error: Task 'missing1' not found in the current project." in result.output
    assert "Traceback" not in result.output


def test_memory_related_to_task_foreign_error(tmp_db, project, monkeypatch) -> None:
    """memory related-to-task rejects foreign task belonging to another project."""
    runner = make_runner_with_project(monkeypatch, project)
    other_project = Project.create("other", "Other", repo_paths=["/tmp/other"])
    foreign_task = Task.create(project_id=other_project.id, title="Foreign task")

    result = runner.invoke(cli, ["memory", "related-to-task", foreign_task.id])

    assert result.exit_code != 0
    assert (
        f"Error: Task '{foreign_task.id}' is a foreign task belonging to another project."
        in result.output
    )
    assert "Traceback" not in result.output


def test_memory_related_to_task_success(tmp_db, project, monkeypatch) -> None:
    """memory related-to-task displays packed memories in a Rich Table for a valid task."""
    runner = make_runner_with_project(monkeypatch, project)
    task = Task.create(
        project_id=project.id, title="Solve logic bug", description="FTS matches logic here"
    )

    # Create memory with matching terms
    memory = Memory.create(
        project_id=project.id,
        type="note",
        title="Logic bug hint",
        content="Always use logic and solve the bug cleanly",
        scope="task",
        task_id=task.id,
    )

    result = runner.invoke(cli, ["memory", "related-to-task", task.id])

    assert result.exit_code == 0, result.output
    assert f"Related Memories for Task '{task.id}'" in result.output
    assert memory.id in result.output
    assert "Logic bug hint" in result.output
