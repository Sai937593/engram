"""Tests for context generation (startup and task context)."""

from engram.context import get_startup_context, get_task_context
from engram.context.startup import (
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
from engram.memory_retrieval import (
    StartupTaskMemoryRetrievalResult,
    TaskMemoryPackedItem,
    TaskMemoryPackMetadata,
    TaskMemoryPackResult,
    TaskMemoryRetrievalMetadata,
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


def test_startup_builder_renders_branch_and_is_resuming(project):
    phase = Phase.create(
        project_id=project.id,
        title="Phase Refactor",
        status="active",
    )
    task = Task.create(
        project_id=project.id,
        title="Implement refactoring",
        phase_id=phase.id,
        status="in-progress",
    )

    ctx = build_startup_context(
        project=project,
        active_phase=phase,
        selected_task=task,
        branch="feat/refactor-branch",
        is_resuming=True,
    )

    assert "Selected: resuming" in ctx
    assert "Branch: feat/refactor-branch" in ctx
    assert (
        "Before coding: run engram_memory_search with keywords from the task. Create implementation_plan.md and await user approval before writing code."
        in ctx
    )
    assert "engram_task_get" in ctx
    assert "engram context task" not in ctx

    # Test when is_resuming is False
    ctx_starting = build_startup_context(
        project=project,
        active_phase=phase,
        selected_task=task,
        branch="feat/refactor-branch",
        is_resuming=False,
    )
    assert "Selected: starting" in ctx_starting


def test_startup_builder_handles_no_task_input(project):
    phase = Phase.create(project_id=project.id, title="Phase Empty", status="active")

    ctx = build_startup_context(project=project, active_phase=phase, selected_task=None)

    assert "No current or next task selected." in ctx
    assert "## NEXT ACTION" in ctx


def test_startup_builder_renders_selected_task_relevant_files(project):
    phase = Phase.create(project_id=project.id, title="Phase Files", status="active")
    task = Task.create(
        project_id=project.id,
        title="Task With Relevant Files",
        phase_id=phase.id,
        status="in-progress",
        relevant_files=["src/engram/context_helpers/startup.py", "tests/test_context.py"],
    )

    ctx = build_startup_context(project=project, active_phase=phase, selected_task=task)

    task_section = ctx.split("## CURRENT/NEXT TASK FRAME\n", maxsplit=1)[1].split(
        "\n## PROJECT GUARDRAILS", maxsplit=1
    )[0]
    assert "Relevant files:" in task_section
    assert "- src/engram/context_helpers/startup.py" in task_section
    assert "- tests/test_context.py" in task_section


def test_startup_builder_hides_relevant_files_label_when_selected_task_has_none(project):
    phase = Phase.create(project_id=project.id, title="Phase No Files", status="active")
    task = Task.create(
        project_id=project.id,
        title="Task Without Relevant Files",
        phase_id=phase.id,
        status="in-progress",
    )

    ctx = build_startup_context(project=project, active_phase=phase, selected_task=task)

    task_section = ctx.split("## CURRENT/NEXT TASK FRAME\n", maxsplit=1)[1].split(
        "\n## PROJECT GUARDRAILS", maxsplit=1
    )[0]
    assert "Relevant files:" not in task_section


def test_startup_builder_caps_and_truncates_relevant_file_paths(project):
    phase = Phase.create(project_id=project.id, title="Phase File Cap", status="active")
    long_path = "src/" + ("a" * 48) + "/task_context.py"
    task = Task.create(
        project_id=project.id,
        title="Task With Many Relevant Files",
        phase_id=phase.id,
        status="in-progress",
        relevant_files=[long_path, "tests/test_context.py", "src/engram/models/task.py"],
    )
    options = StartupContextOptions(relevant_file_limit=2, relevant_file_path_char_limit=24)

    ctx = build_startup_context(
        project=project, active_phase=phase, selected_task=task, options=options
    )

    task_section = ctx.split("## CURRENT/NEXT TASK FRAME\n", maxsplit=1)[1].split(
        "\n## PROJECT GUARDRAILS", maxsplit=1
    )[0]
    assert f"- {_compact_with_limit(long_path, 24)}" in task_section
    assert "- tests/test_context.py" in task_section
    assert "- src/engram/models/task.py" not in task_section
    assert "... 1 additional relevant file path(s) hidden by cap." in task_section


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


def test_startup_builder_guardrails_empty_and_separate_from_task_memory_section(project):
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
    assert "No relevant task memories selected." in task_memory_section
    assert "No L0/L1 project guardrails found." not in task_memory_section
    assert "No relevant task memories selected." not in guardrails_section


def test_startup_builder_renders_selected_task_memories_separate_from_guardrails(
    project, monkeypatch
):
    phase = Phase.create(project_id=project.id, title="Phase Task Memories", status="active")
    task = Task.create(
        project_id=project.id,
        title="Render selected task memories",
        phase_id=phase.id,
        status="in-progress",
    )
    Memory.create(
        project_id=project.id,
        type="constraint",
        title="L1 Guardrail",
        content="Guardrails stay separate.",
        scope="project",
        level="L1",
    )

    retrieval_metadata = TaskMemoryRetrievalMetadata(
        project_id=project.id,
        query_task_id=task.id,
        source="fts",
        requested_query_text="query",
        normalized_fts_query="query",
        query_term_count=1,
        query_was_empty=False,
        fallback_used=False,
        fallback_reason=None,
        max_candidates=20,
        scanned_row_count=2,
        returned_candidate_count=2,
    )
    pack_result = TaskMemoryPackResult(
        items=(
            TaskMemoryPackedItem(
                memory_id="m1",
                type="lesson",
                title="Remember fallback behavior",
                content="Startup should continue even when retrieval fails.",
                tags=("retrieval",),
                task_id=task.id,
                retrieval_source="fts",
                fts_rank=-0.4,
                boost_score=3,
                source_candidate_index=0,
                char_count=50,
                was_truncated=False,
            ),
            TaskMemoryPackedItem(
                memory_id="m2",
                type="snippet",
                title="Rendering format",
                content="Keep task memories concise and deterministic.",
                tags=("format",),
                task_id=task.id,
                retrieval_source="fts",
                fts_rank=-0.3,
                boost_score=2,
                source_candidate_index=1,
                char_count=45,
                was_truncated=False,
            ),
        ),
        metadata=TaskMemoryPackMetadata(
            project_id=project.id,
            query_task_id=task.id,
            source="fts",
            section_char_budget=3600,
            preferred_k=6,
            max_k=10,
            max_item_chars=420,
            input_candidate_count=3,
            unique_candidate_count=3,
            selected_item_count=2,
            hidden_item_count=1,
            truncated_item_count=0,
            used_char_count=95,
            section_budget_exhausted=False,
            ordering_fields=("-boost_score", "fts_rank", "memory_id"),
            dedupe_key="memory_id",
        ),
    )
    startup_result = StartupTaskMemoryRetrievalResult(
        query=None,
        retrieval_metadata=retrieval_metadata,
        pack_result=pack_result,
    )
    monkeypatch.setattr(
        "engram.context.startup.builders.orchestrate_startup_task_memory_retrieval",
        lambda **kwargs: startup_result,
    )

    ctx = build_startup_context(project=project, active_phase=phase, selected_task=task)

    guardrails_section = ctx.split("## PROJECT GUARDRAILS\n", maxsplit=1)[1].split(
        "\n## TASK MEMORY CANDIDATES", maxsplit=1
    )[0]
    task_memory_section = ctx.split("## TASK MEMORY CANDIDATES\n", maxsplit=1)[1].split(
        "\n## NEXT ACTION", maxsplit=1
    )[0]
    assert "L1 Guardrail" in guardrails_section
    assert "Remember fallback behavior" not in guardrails_section
    assert "Rendering format" not in guardrails_section
    assert "Remember fallback behavior" in task_memory_section
    assert "Rendering format" in task_memory_section
    assert "... 1 additional task memory candidate(s) hidden by cap." in task_memory_section


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


def test_startup_builder_task_memory_empty_state_compaction_is_deterministic(project):
    options = StartupContextOptions(
        task_memory_empty_state_text="empty-state " + ("p" * 200),
        task_memory_empty_state_char_limit=40,
    )

    first = build_startup_context(project=project, options=options)
    second = build_startup_context(project=project, options=options)

    assert first == second
    assert "empty-state " in first
    assert "empty-state " + ("p" * 200) not in first
    empty_state_line = first.split("## TASK MEMORY CANDIDATES\n", maxsplit=1)[1].split(
        "\n", maxsplit=1
    )[0]
    assert empty_state_line.endswith("...")
    assert len(empty_state_line) == 40


def test_task_context_shows_title(task):
    ctx = get_task_context(task.id)
    assert task.title in ctx


def test_task_context_renders_relevant_file_paths_when_present(project):
    task_item = Task.create(
        project_id=project.id,
        title="Task Context Relevant Files",
        relevant_files=["src/engram/context_helpers/task.py", "tests/test_context.py"],
    )

    ctx = get_task_context(task_item.id)

    assert "## RELEVANT FILES" in ctx
    assert "- src/engram/context_helpers/task.py" in ctx
    assert "- tests/test_context.py" in ctx


def test_task_context_hides_relevant_files_when_absent(project):
    task_item = Task.create(project_id=project.id, title="Task Context No Relevant Files")

    ctx = get_task_context(task_item.id)

    assert "## RELEVANT FILES" not in ctx


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


def test_startup_context_shows_constraints_first(tmp_db, project, monkeypatch):
    """Startup context includes guardrails and excludes non-guardrail lessons."""
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
    assert "## PROJECT GUARDRAILS" in ctx
    assert "No pip" in ctx
    assert "WAL mode" not in ctx


def test_startup_context_no_tasks_phase_gap(tmp_db, project):
    """Startup context shows no-task guidance when project has zero tasks."""
    ctx = get_startup_context(project.id)
    assert "No tasks are defined yet." in ctx


def test_startup_context_phase_complete(tmp_db, project):
    """Startup context shows completion guidance when all work is finished."""
    Task.create(project_id=project.id, title="Done", status="done")
    ctx = get_startup_context(project.id)
    assert "All 1 tasks are done or cancelled." in ctx


def test_task_context_includes_project_knowledge(tmp_db, project, task):
    """Task context includes project-wide constraints and lessons."""
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


def test_compact_text_handles_none_empty_and_non_ascii() -> None:
    from engram.context.common import compact_text

    assert compact_text(None) == ""
    assert compact_text("") == ""
    assert compact_text("snowman ☃") == "snowman ?"


def test_startup_context_returns_project_not_found_for_unknown_id(tmp_db) -> None:
    assert build_startup_context("missing-project") == "Project not found."


def test_task_matches_phase_uses_phase_id_before_legacy_title(project) -> None:
    from engram.context.startup.orchestrator import _task_matches_phase

    phase = Phase.create(project_id=project.id, id="phmatch1", title="Legacy Title", status="active")
    matching_id = Task.create(
        project_id=project.id,
        title="Matching id",
        phase_id=phase.id,
        phase="Other title",
    )
    mismatched_id = Task.create(
        project_id=project.id,
        title="Mismatched id",
        phase_id="different",
        phase=phase.title,
    )
    legacy_match = Task.create(project_id=project.id, title="Legacy", phase=" legacy title ")

    assert _task_matches_phase(matching_id, phase) is True
    assert _task_matches_phase(mismatched_id, phase) is False
    assert _task_matches_phase(legacy_match, phase) is True


def test_resolve_default_startup_inputs_prefers_in_progress_active_phase_task(project) -> None:
    from engram.context.startup.orchestrator import _resolve_default_startup_inputs

    phase = Phase.create(project_id=project.id, id="phres001", title="Phase A", status="active")
    Task.create(project_id=project.id, title="Todo", phase_id=phase.id, status="todo")
    in_progress = Task.create(
        project_id=project.id,
        title="In progress",
        phase_id=phase.id,
        status="in-progress",
    )

    resolved_phase, resolved_task = _resolve_default_startup_inputs(project.id)

    assert resolved_phase.id == phase.id
    assert resolved_task.id == in_progress.id


def test_resolve_default_startup_inputs_falls_back_to_in_progress_any(project) -> None:
    from engram.context.startup.orchestrator import _resolve_default_startup_inputs

    phase = Phase.create(project_id=project.id, id="phres002", title="Phase B", status="active")
    outside_phase = Task.create(project_id=project.id, title="Outside", status="in-progress")

    resolved_phase, resolved_task = _resolve_default_startup_inputs(project.id)

    assert resolved_phase.id == phase.id
    assert resolved_task.id == outside_phase.id


def test_context_package_lazy_snapshot_and_handoff_wrappers(project) -> None:
    from engram.context import get_handoff_context, get_snapshot_context

    snapshot = get_snapshot_context(project.id)
    handoff = get_handoff_context(project.id)

    assert "# PROJECT SNAPSHOT: Test Project" in snapshot
    assert "# PROJECT HANDOFF: Test Project" in handoff
