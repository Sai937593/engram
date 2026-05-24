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
        level="L1",
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

    # Normal ASCII
    assert _compact_text("Hello World") == "Hello World"

    # Unicode replacement
    assert _compact_text("Hello \u2665 World") == "Hello ? World"

    # Verify no truncation occurs on long strings
    long_str = "a" * 200
    assert _compact_text(long_str) == long_str


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

    # Goal should show "?" instead of "\u2605", and not be truncated
    assert "Goal: Deliver ? star products: " in ctx
    assert "..." not in ctx.split("Goal: ")[1].split("\n")[0]
    assert len(ctx.split("Goal: ")[1].split("\n")[0]) == len("Deliver ? star products: ") + 200

    # Acceptance should not be truncated and should be ASCII-safe
    assert "Acceptance: Acceptance criteria is very long: " + ("y" * 200) in ctx

    # Evidence should not be truncated and should be ASCII-safe
    assert "Evidence: Evidence that we delivered: " + ("z" * 200) in ctx


def test_task_context_shows_short_phase_details_fully(project):
    from engram.models.phase import Phase

    phase = Phase.create(
        project_id=project.id,
        title="Short Phase",
        description="Goal is simple.",
        status="active",
        acceptance="Acceptance is simple.",
        evidence="Evidence is simple.",
    )
    t = Task.create(
        project_id=project.id,
        title="Task in short phase",
        phase_id=phase.id,
    )
    ctx = get_task_context(t.id)

    assert "## PHASE" in ctx
    assert "Phase: Short Phase (Status: active)" in ctx
    assert "Goal: Goal is simple." in ctx
    assert "Acceptance: Acceptance is simple." in ctx
    assert "Evidence: Evidence is simple." in ctx
    # Ensure there is no trailing ellipsis in these short texts
    assert "..." not in ctx.split("Goal: ")[1].split("\n")[0]


def test_task_context_phase_no_extra_fields(project):
    from engram.models.phase import Phase

    phase = Phase.create(
        project_id=project.id,
        title="Empty Phase Fields",
        status="active",
    )
    t = Task.create(
        project_id=project.id,
        title="Task in empty field phase",
        phase_id=phase.id,
    )
    ctx = get_task_context(t.id)

    assert "## PHASE" in ctx
    assert "Phase: Empty Phase Fields (Status: active)" in ctx
    assert "Goal:" not in ctx
    assert "Acceptance:" not in ctx
    assert "Evidence:" not in ctx


def test_task_context_phase_evidence_truncation_exactly(project):
    from engram.models.phase import Phase

    long_evidence = "Evidence is: " + ("e" * 300)
    phase = Phase.create(
        project_id=project.id,
        title="Phase Evidence Truncation",
        status="active",
        evidence=long_evidence,
    )
    t = Task.create(
        project_id=project.id,
        title="Task with long evidence phase",
        phase_id=phase.id,
    )
    ctx = get_task_context(t.id)

    # Check evidence line
    evidence_line = ctx.split("Evidence: ")[1].split("\n")[0]
    assert len(evidence_line) == len("Evidence is: ") + 300
    assert not evidence_line.endswith("...")
    assert evidence_line == "Evidence is: " + ("e" * 300)


def test_task_context_phase_formatting_stability(project):
    from engram.models.phase import Phase

    # Test stability with special characters, emojis, newlines, and varied sizes
    phase = Phase.create(
        project_id=project.id,
        title="Stable Phase",
        description="Line 1\nLine 2\nLine 3 with unicode \u2728",
        status="active",
        acceptance="Short.",
        evidence="Evidence line 1\nEvidence line 2 with a lot of details: " + ("w" * 200),
    )
    t = Task.create(
        project_id=project.id,
        title="Task in stable phase",
        phase_id=phase.id,
    )
    ctx = get_task_context(t.id)

    assert "## PHASE" in ctx
    assert "Phase: Stable Phase (Status: active)" in ctx
    assert "Goal: Line 1" in ctx
    assert "Line 2" in ctx
    assert "Line 3 with unicode ?" in ctx
    assert "Acceptance: Short." in ctx

    # Evidence has newlines and is long, check it has "?" replaced if any (though 'w' is ASCII),
    # and that it is truncated. Let's inspect the entire evidence block in ctx.
    evidence_part = ctx.split("Evidence: ")[1]
    # It starts with "Evidence line 1"
    assert evidence_part.startswith("Evidence line 1")

    # To be extremely precise and stable:
    from engram.context import _compact_text

    compacted_evidence = _compact_text(phase.evidence)
    assert compacted_evidence in ctx
    assert (
        len(compacted_evidence)
        == len("Evidence line 1\nEvidence line 2 with a lot of details: ") + 200
    )
    assert not compacted_evidence.endswith("...")
