"""Tests for context generation (startup and task context)."""

from engram.context import get_startup_context, get_task_context
from engram.models.memory import Memory
from engram.models.task import Task


def test_startup_context_contains_project_name(project):
    ctx = get_startup_context(project.id)
    assert "Test Project" in ctx


def test_startup_context_shows_always_include_memories(project):
    Memory.create(
        project_id=project.id,
        type="constraint",
        title="Never write to prod",
        content="Do not touch production DB.",
        always_include=True,
    )
    ctx = get_startup_context(project.id)
    assert "Never write to prod" in ctx


def test_startup_context_shows_active_tasks(project):
    Task.create(project_id=project.id, title="My active task", status="todo")
    ctx = get_startup_context(project.id)
    assert "My active task" in ctx


def test_startup_context_no_crash_when_empty(project):
    """Startup context should work gracefully even with no tasks or sessions."""
    ctx = get_startup_context(project.id)
    assert "Test Project" in ctx


def test_task_context_shows_title(task):
    ctx = get_task_context(task.id)
    assert task.title in ctx


def test_task_context_shows_acceptance(project):
    t = Task.create(
        project_id=project.id,
        title="Feature with acceptance",
        acceptance="Must pass all unit tests.",
    )
    ctx = get_task_context(t.id)
    assert "Must pass all unit tests." in ctx


def test_task_context_not_found():
    ctx = get_task_context("nonexistent-id")
    assert "not found" in ctx.lower()


def test_task_context_shows_phase_info(project):
    from engram.models.phase import Phase

    phase = Phase.create(
        project_id=project.id,
        title="Phase Roadmap",
        description="Deliver the roadmap features",
        status="active",
    )
    t = Task.create(
        project_id=project.id,
        title="Task in phase",
        phase_id=phase.id,
    )
    ctx = get_task_context(t.id)
    assert "## PHASE" in ctx
    assert "Phase: Phase Roadmap (Status: active)" in ctx
    assert "Goal: Deliver the roadmap features" in ctx


def test_task_context_shows_legacy_phase_info(project):
    t = Task.create(
        project_id=project.id,
        title="Task in legacy phase",
        phase="Phase Legacy",
    )
    ctx = get_task_context(t.id)
    assert "## PHASE" in ctx
    assert "Phase: Phase Legacy" in ctx


def test_compact_text():
    from engram.context import _compact_text

    # None and empty
    assert _compact_text(None) == ""
    assert _compact_text("") == ""

    # Normal short ASCII
    assert _compact_text("Hello World") == "Hello World"

    # Unicode replacement
    assert _compact_text("Hello \u2665 World") == "Hello ? World"

    # Truncation
    long_str = "a" * 200
    truncated = _compact_text(long_str, max_chars=50)
    assert len(truncated) == 50
    assert truncated.endswith("...")
    assert truncated == "a" * 47 + "..."

    # Truncation with very small max_chars
    assert _compact_text("abcdef", max_chars=3) == "..."


def test_task_context_shows_compact_phase_details(project):
    from engram.models.phase import Phase

    phase = Phase.create(
        project_id=project.id,
        title="Phase Custom",
        description="Deliver \u2605 star products: " + ("x" * 200),
        status="active",
        acceptance="Acceptance criteria is very long: " + ("y" * 200),
        evidence="Evidence that we delivered: " + ("z" * 200),
    )
    t = Task.create(
        project_id=project.id,
        title="Task in detailed phase",
        phase_id=phase.id,
    )
    ctx = get_task_context(t.id)

    assert "## PHASE" in ctx
    assert "Phase: Phase Custom (Status: active)" in ctx

    # Goal should show "?" instead of "\u2605", and be truncated at 150 chars total
    # "Goal: " takes 6 chars. 150 limit on _compact_text. Total line limit around 156.
    assert "Goal: Deliver ? star products: " in ctx
    assert "..." in ctx
    assert len(ctx.split("Goal: ")[1].split("\n")[0]) == 150

    # Acceptance should be truncated and ASCII-safe
    assert "Acceptance: Acceptance criteria is very long: " in ctx

    # Evidence should be truncated and ASCII-safe
    assert "Evidence: Evidence that we delivered: " in ctx
