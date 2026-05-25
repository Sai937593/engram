"""CLI tests for guardrail demotion command behavior."""

from click.testing import CliRunner

from engram.cli import cli
from engram.db import get_db_connection
from engram.models.memory import Memory
from engram.models.project import Project


def make_runner_with_project(monkeypatch, project) -> CliRunner:
    """Return a CliRunner with current-project resolution patched."""
    monkeypatch.setattr("engram.cli.get_current_project", lambda: project)
    return CliRunner()


def test_guardrail_demote_success(tmp_db, project, monkeypatch) -> None:
    """guardrail demote lowers exactly one level for a valid project memory."""
    runner = make_runner_with_project(monkeypatch, project)
    memory = Memory.create(
        project_id=project.id,
        type="note",
        title="Guardrail",
        content="Protect startup quality.",
        scope="project",
        level="L0",
    )

    result = runner.invoke(
        cli,
        ["guardrail", "demote", memory.id, "--reason", "Too strict for current phase."],
    )

    assert result.exit_code == 0, result.output
    assert f"Guardrail '{memory.id}' demoted: L0 -> L1" in result.output
    refreshed = Memory.get(memory.id)
    assert refreshed is not None
    assert refreshed.level == "L1"


def test_guardrail_demote_requires_non_empty_reason(tmp_db, project, monkeypatch) -> None:
    """guardrail demote rejects whitespace-only reasons."""
    runner = make_runner_with_project(monkeypatch, project)
    memory = Memory.create(
        project_id=project.id,
        type="constraint",
        title="Guardrail",
        content="Protect startup quality.",
        scope="project",
        level="L1",
    )

    result = runner.invoke(cli, ["guardrail", "demote", memory.id, "--reason", "   "])

    assert result.exit_code != 0
    assert "Error: Demotion reason cannot be empty." in result.output


def test_guardrail_demote_rejects_l3(tmp_db, project, monkeypatch) -> None:
    """guardrail demote fails clearly when memory is already at L3."""
    runner = make_runner_with_project(monkeypatch, project)
    memory = Memory.create(
        project_id=project.id,
        type="note",
        title="Low memory",
        content="Already at lowest level.",
        scope="project",
        level="L3",
    )

    result = runner.invoke(
        cli,
        ["guardrail", "demote", memory.id, "--reason", "Need to relax it further."],
    )

    assert result.exit_code != 0
    assert "already at the lowest level (L3)" in result.output


def test_guardrail_demote_rejects_non_project_scope(tmp_db, project, monkeypatch) -> None:
    """guardrail demote rejects task-scope memories."""
    runner = make_runner_with_project(monkeypatch, project)
    memory = Memory.create(
        project_id=project.id,
        type="lesson",
        title="Task memory",
        content="Task-only learning.",
        scope="task",
        task_id="task-123",
        level=None,
    )

    result = runner.invoke(
        cli,
        ["guardrail", "demote", memory.id, "--reason", "Not needed as guardrail."],
    )

    assert result.exit_code != 0
    assert "Only project-scope memories can be demoted." in result.output


def test_guardrail_demote_rejects_missing_and_foreign_ids(tmp_db, project, monkeypatch) -> None:
    """guardrail demote reports missing and foreign memory IDs clearly."""
    runner = make_runner_with_project(monkeypatch, project)
    other_project = Project.create("other-project", "Other", repo_paths=["/tmp/other"])
    foreign_memory = Memory.create(
        project_id=other_project.id,
        type="constraint",
        title="Foreign guardrail",
        content="Belongs elsewhere.",
        scope="project",
        level="L1",
    )

    missing = runner.invoke(
        cli, ["guardrail", "demote", "missing1", "--reason", "Need lower level."]
    )
    assert missing.exit_code != 0
    assert "Memory 'missing1' not found in the current project." in missing.output

    foreign = runner.invoke(
        cli,
        ["guardrail", "demote", foreign_memory.id, "--reason", "Need lower level."],
    )
    assert foreign.exit_code != 0
    assert "is a foreign memory belonging to another project." in foreign.output


def test_guardrail_demote_rejects_ambiguous_prefix(tmp_db, project, monkeypatch) -> None:
    """guardrail demote fails when a prefix matches multiple memories."""
    runner = make_runner_with_project(monkeypatch, project)
    Memory.create(
        id="abcd1111",
        project_id=project.id,
        type="constraint",
        title="A",
        content="A",
        scope="project",
        level="L1",
    )
    Memory.create(
        id="abcd2222",
        project_id=project.id,
        type="constraint",
        title="B",
        content="B",
        scope="project",
        level="L1",
    )

    result = runner.invoke(
        cli,
        ["guardrail", "demote", "abcd", "--reason", "Need lower level."],
    )

    assert result.exit_code != 0
    assert "Ambiguous memory 'abcd'. Multiple matches found:" in result.output


def test_guardrail_demote_rejects_invalid_level_rows(tmp_db, project, monkeypatch) -> None:
    """guardrail demote fails clearly for invalid legacy levels."""
    runner = make_runner_with_project(monkeypatch, project)
    conn = get_db_connection(tmp_db)
    conn.execute(
        """
        INSERT INTO memories (
            id, project_id, type, title, content, scope, level, task_id, tags, always_include
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "legacybad",
            project.id,
            "note",
            "Legacy bad",
            "Bad level row.",
            "project",
            "L9",
            None,
            "",
            0,
        ),
    )
    conn.commit()
    conn.close()

    result = runner.invoke(
        cli,
        ["guardrail", "demote", "legacybad", "--reason", "Need lower level."],
    )

    assert result.exit_code != 0
    assert "has invalid level 'L9'" in result.output
