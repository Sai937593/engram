"""Tests for context generation (startup and task context)."""

from engram.context import get_startup_context, get_task_context
from engram.context_helpers.startup import (
    CONTEXT_TRUNCATION_MARKER,
    STARTUP_HARD_CHAR_BUDGET,
    STARTUP_HARD_TOKEN_BUDGET,
    STARTUP_TARGET_CHAR_BUDGET_MAX,
    STARTUP_TARGET_CHAR_BUDGET_MIN,
    STARTUP_TARGET_TOKEN_BUDGET_MAX,
    STARTUP_TARGET_TOKEN_BUDGET_MIN,
    TOKEN_TO_CHAR_APPROX,
    StartupContextOptions,
    _compact_with_limit,
    _enforce_hard_budget,
    build_startup_context,
)
from engram.models.memory import Memory
from engram.models.phase import Phase
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


def test_startup_builder_accepts_project_phase_and_task(project):
    phase = Phase.create(
        project_id=project.id,
        title="Phase Builder",
        status="active",
        description="Deliver the startup builder contract.",
    )
    task = Task.create(
        project_id=project.id,
        title="Implement startup builder",
        phase_id=phase.id,
        status="in-progress",
        acceptance="Startup context uses unified sections.",
    )
    Memory.create(
        project_id=project.id,
        type="constraint",
        title="Local-first only",
        content="Avoid remote dependencies.",
        level="L1",
    )

    ctx = build_startup_context(project=project, active_phase=phase, selected_task=task)

    assert "## PROJECT FRAME" in ctx
    assert "## CURRENT PHASE FRAME" in ctx
    assert "## CURRENT/NEXT TASK FRAME" in ctx
    assert "## PROJECT GUARDRAILS" in ctx
    assert "## TASK MEMORY CANDIDATES" in ctx
    assert "## NEXT ACTION" in ctx
    assert "Implement startup builder" in ctx
    assert "Local-first only" in ctx


def test_startup_builder_handles_no_task_input(project):
    phase = Phase.create(project_id=project.id, title="Phase Empty", status="active")

    ctx = build_startup_context(project=project, active_phase=phase, selected_task=None)

    assert "No current or next task selected." in ctx
    assert "## NEXT ACTION" in ctx


def test_startup_builder_caps_l1_guardrails(project):
    Memory.create(
        id="l0a00001",
        project_id=project.id,
        type="constraint",
        title="Identity",
        content="Core identity memory.",
        level="L0",
    )
    Memory.create(
        id="l1a00001",
        project_id=project.id,
        type="constraint",
        title="Constraint A",
        content="A",
        level="L1",
    )
    Memory.create(
        id="l1b00001",
        project_id=project.id,
        type="constraint",
        title="Constraint B",
        content="B",
        level="L1",
    )
    Memory.create(
        id="l1c00001",
        project_id=project.id,
        type="constraint",
        title="Constraint C",
        content="C",
        level="L1",
    )

    ctx = build_startup_context(
        project=project,
        options=StartupContextOptions(l1_guardrail_limit=2),
    )

    assert "Identity" in ctx
    assert "Constraint A" in ctx
    assert "Constraint B" in ctx
    assert "Constraint C" not in ctx
    assert "hidden by cap" in ctx


def test_startup_builder_guardrails_use_project_l0_l1_only_in_order(project):
    Memory.create(
        id="l1b00002",
        project_id=project.id,
        type="constraint",
        title="L1 B",
        content="Project L1 B",
        scope="project",
        level="L1",
    )
    Memory.create(
        id="l2a00002",
        project_id=project.id,
        type="decision",
        title="L2 decision",
        content="Should not appear in guardrails.",
        scope="project",
        level="L2",
    )
    Memory.create(
        id="l0a00002",
        project_id=project.id,
        type="constraint",
        title="L0 Identity",
        content="Project L0 identity",
        scope="project",
        level="L0",
    )
    Memory.create(
        id="l1a00002",
        project_id=project.id,
        type="constraint",
        title="L1 A",
        content="Project L1 A",
        scope="project",
        level="L1",
    )
    task = Task.create(project_id=project.id, title="Scoped memory task", status="in-progress")
    Memory.create(
        id="taskm001",
        project_id=project.id,
        task_id=task.id,
        type="lesson",
        title="Task lesson",
        content="Task-scope memory should not appear in guardrails.",
        scope="task",
    )
    Memory.create(
        id="l3a00002",
        project_id=project.id,
        type="snippet",
        title="L3 snippet",
        content="Should not appear in guardrails.",
        scope="project",
        level="L3",
    )

    ctx = build_startup_context(project=project)

    guardrails_section = ctx.split("## PROJECT GUARDRAILS\n", maxsplit=1)[1].split(
        "\n## TASK MEMORY CANDIDATES", maxsplit=1
    )[0]
    assert "L0 Identity" in guardrails_section
    assert "L1 A" in guardrails_section
    assert "L1 B" in guardrails_section
    assert "L2 decision" not in guardrails_section
    assert "L3 snippet" not in guardrails_section
    assert "Task lesson" not in guardrails_section
    assert guardrails_section.find("L0 Identity") < guardrails_section.find("L1 A")
    assert guardrails_section.find("L1 A") < guardrails_section.find("L1 B")


def test_startup_builder_guardrails_empty_and_separate_from_task_memory_placeholder(project):
    ctx = build_startup_context(project=project)

    assert "No L0/L1 project guardrails found." in ctx
    guardrails_index = ctx.index("## PROJECT GUARDRAILS")
    task_memory_index = ctx.index("## TASK MEMORY CANDIDATES")
    assert guardrails_index < task_memory_index

    guardrails_section = ctx.split("## PROJECT GUARDRAILS\n", maxsplit=1)[1].split(
        "\n## TASK MEMORY CANDIDATES", maxsplit=1
    )[0]
    task_memory_section = ctx.split("## TASK MEMORY CANDIDATES\n", maxsplit=1)[1].split(
        "\n## NEXT ACTION", maxsplit=1
    )[0]
    assert (
        "Retrieval is not enabled in this phase. Placeholder section only." in task_memory_section
    )
    assert "No L0/L1 project guardrails found." not in task_memory_section
    assert (
        "Retrieval is not enabled in this phase. Placeholder section only."
        not in guardrails_section
    )


def test_startup_builder_compacts_text_and_enforces_hard_budget(project):
    phase = Phase.create(
        project_id=project.id,
        title="Phase Long",
        status="active",
        description="phase " + ("p" * 200),
    )
    task = Task.create(
        project_id=project.id,
        title="Task Long",
        phase_id=phase.id,
        status="todo",
        description="desc " + ("d" * 200),
    )
    project.update(summary="summary " + ("s" * 200))

    ctx = build_startup_context(
        project=project,
        active_phase=phase,
        selected_task=task,
        options=StartupContextOptions(
            hard_char_budget=450,
            project_summary_char_limit=40,
            phase_text_char_limit=40,
            task_text_char_limit=40,
        ),
    )

    assert "..." in ctx
    assert len(ctx) <= 450
    assert ctx.endswith("[Context truncated to fit budget.]")


def test_startup_budget_constants_match_design_plan():
    assert TOKEN_TO_CHAR_APPROX == 4
    assert STARTUP_TARGET_TOKEN_BUDGET_MIN == 1500
    assert STARTUP_TARGET_TOKEN_BUDGET_MAX == 2000
    assert STARTUP_HARD_TOKEN_BUDGET == 3000
    assert STARTUP_TARGET_CHAR_BUDGET_MIN == 6000
    assert STARTUP_TARGET_CHAR_BUDGET_MAX == 8000
    assert STARTUP_HARD_CHAR_BUDGET == 12000


def test_compact_with_limit_boundaries_and_empty_input():
    assert _compact_with_limit(None, 20) == ""
    assert _compact_with_limit("", 20) == ""
    assert _compact_with_limit("hello", 0) == ""
    assert _compact_with_limit("abc", 3) == "abc"
    assert _compact_with_limit("abcd", 3) == "abc"
    assert _compact_with_limit("abcd", 4) == "abcd"
    assert _compact_with_limit("abcde", 4) == "a..."


def test_enforce_hard_budget_boundaries_and_marker():
    exact = "abcd"
    assert _enforce_hard_budget(exact, 4) == exact

    over = "abcde"
    result = _enforce_hard_budget(over, 4)
    assert result == CONTEXT_TRUNCATION_MARKER[:4]

    larger_budget_result = _enforce_hard_budget("x" * 100, 60)
    assert len(larger_budget_result) <= 60
    assert larger_budget_result.endswith("[Context truncated to fit budget.]")


def test_startup_builder_placeholder_compaction_is_deterministic(project):
    options = StartupContextOptions(
        task_memory_placeholder_text="placeholder " + ("p" * 200),
        task_memory_placeholder_char_limit=40,
    )

    first = build_startup_context(project=project, options=options)
    second = build_startup_context(project=project, options=options)

    assert first == second
    assert "placeholder " in first
    assert "placeholder " + ("p" * 200) not in first
    placeholder_line = first.split("## TASK MEMORY CANDIDATES\n", maxsplit=1)[1].split(
        "\n", maxsplit=1
    )[0]
    assert placeholder_line.endswith("...")
    assert len(placeholder_line) == 40


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
