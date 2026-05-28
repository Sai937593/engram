"""Startup context rendering."""

from __future__ import annotations

from dataclasses import dataclass

from engram.context_helpers.common import compact_text
from engram.memory_retrieval import (
    StartupTaskMemoryRetrievalResult,
    orchestrate_startup_task_memory_retrieval,
)
from engram.models.memory import Memory
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task, get_effective_phase_title

TOKEN_TO_CHAR_APPROX = 4
STARTUP_TARGET_TOKEN_BUDGET_MIN = 1500
STARTUP_TARGET_TOKEN_BUDGET_MAX = 2000
STARTUP_HARD_TOKEN_BUDGET = 3000
STARTUP_TARGET_CHAR_BUDGET_MIN = STARTUP_TARGET_TOKEN_BUDGET_MIN * TOKEN_TO_CHAR_APPROX
STARTUP_TARGET_CHAR_BUDGET_MAX = STARTUP_TARGET_TOKEN_BUDGET_MAX * TOKEN_TO_CHAR_APPROX
STARTUP_HARD_CHAR_BUDGET = STARTUP_HARD_TOKEN_BUDGET * TOKEN_TO_CHAR_APPROX
CONTEXT_TRUNCATION_MARKER = "\n\n[Context truncated to fit budget.]"


@dataclass(frozen=True)
class StartupContextOptions:
    """Configuration for deterministic startup context rendering."""

    target_char_budget: int = STARTUP_TARGET_CHAR_BUDGET_MAX
    hard_char_budget: int = STARTUP_HARD_CHAR_BUDGET
    project_summary_char_limit: int = 400
    phase_text_char_limit: int = 400
    task_text_char_limit: int = 500
    guardrail_text_char_limit: int = 220
    task_memory_empty_state_text: str = "No relevant task memories selected."
    task_memory_empty_state_char_limit: int = 220
    task_memory_item_title_char_limit: int = 100
    task_memory_item_content_char_limit: int = 260
    l1_guardrail_limit: int = 6
    relevant_file_limit: int = 5
    relevant_file_path_char_limit: int = 120


def _compact_with_limit(text: str | None, char_limit: int) -> str:
    """Convert text to ASCII and truncate deterministically when needed."""
    compacted = compact_text(text)
    if not compacted or char_limit <= 0:
        return ""
    if len(compacted) <= char_limit:
        return compacted
    if char_limit <= 3:
        return compacted[:char_limit]
    return compacted[: char_limit - 3].rstrip() + "..."


def _enforce_hard_budget(rendered: str, hard_char_budget: int) -> str:
    """Cap output length with a deterministic truncation marker."""
    if hard_char_budget <= 0:
        return ""
    if len(rendered) <= hard_char_budget:
        return rendered

    if hard_char_budget <= len(CONTEXT_TRUNCATION_MARKER):
        return CONTEXT_TRUNCATION_MARKER[:hard_char_budget]

    visible = rendered[: hard_char_budget - len(CONTEXT_TRUNCATION_MARKER)].rstrip()
    return f"{visible}{CONTEXT_TRUNCATION_MARKER}"


def _render_section(title: str, lines: list[str]) -> str:
    """Render one startup section block."""
    rendered_lines = [f"## {title}"]
    rendered_lines.extend(line for line in lines if line)
    return "\n".join(rendered_lines)


def _build_project_frame(project: Project, options: StartupContextOptions) -> str:
    lines = [f"Name: {project.name}"]
    summary = _compact_with_limit(project.summary, options.project_summary_char_limit)
    if summary:
        lines.append(f"Summary: {summary}")
    return _render_section("PROJECT FRAME", lines)


def _build_phase_frame(active_phase: Phase | None, options: StartupContextOptions) -> str:
    if not active_phase:
        return _render_section("CURRENT PHASE FRAME", ["No active phase selected."])

    lines = [
        f"Phase: {active_phase.title} ({active_phase.id})",
        f"Status: {active_phase.status}",
    ]
    goal = _compact_with_limit(active_phase.description, options.phase_text_char_limit)
    acceptance = _compact_with_limit(active_phase.acceptance, options.phase_text_char_limit)
    if goal:
        lines.append(f"Goal: {goal}")
    if acceptance:
        lines.append(f"Acceptance: {acceptance}")
    return _render_section("CURRENT PHASE FRAME", lines)


def _build_task_frame(
    selected_task: Task | None,
    options: StartupContextOptions,
    branch: str | None = None,
    is_resuming: bool | None = None,
) -> str:
    if not selected_task:
        return _render_section("CURRENT/NEXT TASK FRAME", ["No current or next task selected."])

    task_slot = "current" if selected_task.status == "in-progress" else "next"
    selected_val = (
        "resuming" if is_resuming else "starting" if is_resuming is not None else task_slot
    )
    lines = [
        f"Selected: {selected_val}",
        f"Task: {selected_task.title} ({selected_task.id})",
        f"Status: {selected_task.status}",
        f"Priority: {selected_task.priority}",
    ]
    if branch:
        lines.append(f"Branch: {branch}")
    effective_phase_title = get_effective_phase_title(selected_task)
    if effective_phase_title:
        lines.append(f"Phase: {effective_phase_title}")

    description = _compact_with_limit(selected_task.description, options.task_text_char_limit)
    acceptance = _compact_with_limit(selected_task.acceptance, options.task_text_char_limit)
    if description:
        lines.append(f"Description: {description}")
    if acceptance:
        lines.append(f"Acceptance: {acceptance}")
    if selected_task.tags:
        lines.append(f"Tags: {', '.join(selected_task.tags)}")
    if selected_task.relevant_files:
        lines.append("")
        lines.append("Relevant files:")
        capped_paths = selected_task.relevant_files[: options.relevant_file_limit]
        for path in capped_paths:
            compact_path = _compact_with_limit(path, options.relevant_file_path_char_limit)
            if compact_path:
                lines.append(f"- {compact_path}")
        hidden_path_count = max(0, len(selected_task.relevant_files) - len(capped_paths))
        if hidden_path_count:
            lines.append(f"... {hidden_path_count} additional relevant file path(s) hidden by cap.")

    return _render_section("CURRENT/NEXT TASK FRAME", lines)


def _build_guardrail_frame(project_id: str, options: StartupContextOptions) -> str:
    guardrails = Memory.list_project_guardrail_candidates(project_id)
    l0_guardrails = [memory for memory in guardrails if memory.level == "L0"]
    l1_guardrails = [memory for memory in guardrails if memory.level == "L1"]
    capped_l1 = l1_guardrails[: options.l1_guardrail_limit]
    hidden_l1_count = max(0, len(l1_guardrails) - len(capped_l1))

    lines: list[str] = []
    if not l0_guardrails and not capped_l1:
        lines.append("No L0/L1 project guardrails found.")
        return _render_section("PROJECT GUARDRAILS", lines)

    if l0_guardrails:
        lines.append("L0 Identity:")
        for memory in l0_guardrails:
            content = _compact_with_limit(memory.content, options.guardrail_text_char_limit)
            lines.append(f"- {memory.title}: {content}")

    if capped_l1:
        lines.append("L1 Constraints:")
        for memory in capped_l1:
            content = _compact_with_limit(memory.content, options.guardrail_text_char_limit)
            lines.append(f"- {memory.title}: {content}")

    if hidden_l1_count:
        lines.append(f"... {hidden_l1_count} additional L1 guardrail(s) hidden by cap.")

    return _render_section("PROJECT GUARDRAILS", lines)


def _build_task_memory_candidates_frame(
    project: Project,
    active_phase: Phase | None,
    selected_task: Task | None,
    options: StartupContextOptions,
    retrieval_result: StartupTaskMemoryRetrievalResult | None = None,
) -> str:
    result = retrieval_result or orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=active_phase,
        selected_task=selected_task,
    )
    lines: list[str] = []
    packed_items = result.pack_result.items

    if not packed_items:
        empty_state = _compact_with_limit(
            options.task_memory_empty_state_text,
            options.task_memory_empty_state_char_limit,
        )
        if empty_state:
            lines.append(empty_state)
        return _render_section("TASK MEMORY CANDIDATES", lines)

    for item in packed_items:
        item_type = _compact_with_limit(item.type, 30)
        title = _compact_with_limit(item.title, options.task_memory_item_title_char_limit)
        content = _compact_with_limit(item.content, options.task_memory_item_content_char_limit)
        if title and content:
            lines.append(f"- [{item_type}] {title}: {content}")
        elif title:
            lines.append(f"- [{item_type}] {title}")
        elif content:
            lines.append(f"- [{item_type}] {content}")
        else:
            lines.append(f"- [{item_type}]")

    hidden_count = result.pack_result.metadata.hidden_item_count
    if hidden_count > 0:
        lines.append(f"... {hidden_count} additional task memory candidate(s) hidden by cap.")

    return _render_section("TASK MEMORY CANDIDATES", lines)


def _build_next_action(project: Project, selected_task: Task | None) -> str:
    if selected_task:
        return _render_section(
            "NEXT ACTION",
            [
                f"Use this startup context to implement: {selected_task.title} ({selected_task.id}).",
                f"If deeper context is needed: engram_task_get {selected_task.id}",
                "Before coding: run engram_memory_search with keywords from the task. Create implementation_plan.md and await user approval before writing code.",
            ],
        )

    counts = Task.count_by_status(project.id)
    total = sum(counts.values())
    pending = sum(count for status, count in counts.items() if status not in ("done", "cancelled"))

    if total == 0:
        return _render_section(
            "NEXT ACTION",
            [
                "No tasks are defined yet.",
                "Ask the user for the next phase and start it using engram_phase_start, then create a task using engram_task_create.",
            ],
        )

    if pending == 0:
        return _render_section(
            "NEXT ACTION",
            [
                f"All {total} tasks are done or cancelled.",
                "Confirm whether to continue planning: create a new task using engram_task_create.",
            ],
        )

    blocked = counts.get("blocked", 0)
    if blocked == pending:
        return _render_section(
            "NEXT ACTION",
            [
                f"All remaining tasks are blocked ({blocked}).",
                "Resolve blockers or re-plan task ordering using engram_task_update.",
            ],
        )

    return _render_section(
        "NEXT ACTION",
        [
            "No startup task selection was provided.",
            "Run engram_workflow_start or engram_task_start to select and start the next actionable task.",
        ],
    )


def _task_matches_phase(task: Task, phase: Phase) -> bool:
    """Return True when task belongs to the phase via phase_id or legacy phase title."""
    if task.phase_id == phase.id:
        return True
    if task.phase_id:
        return False
    return (
        compact_text(task.phase).strip().casefold() == compact_text(phase.title).strip().casefold()
    )


def _resolve_default_startup_inputs(project_id: str) -> tuple[Phase | None, Task | None]:
    """Resolve active phase and selected task for legacy project-id callers."""
    phases = Phase.list_by_project(project_id)
    active_phase = next((phase for phase in phases if phase.status == "active"), None)
    tasks = Task.list_by_project(project_id)

    if active_phase:
        in_progress_active = [
            task
            for task in tasks
            if task.status == "in-progress" and _task_matches_phase(task, active_phase)
        ]
        if in_progress_active:
            return active_phase, in_progress_active[0]

        next_active = Task.get_next_for_phase(project_id, active_phase.id, active_phase.title)
        if next_active:
            return active_phase, next_active

        next_unphased = Task.get_next_unphased(project_id)
        if next_unphased:
            return active_phase, next_unphased

    in_progress_any = [task for task in tasks if task.status == "in-progress"]
    if in_progress_any:
        return active_phase, in_progress_any[0]

    return active_phase, Task.get_next(project_id)


def build_startup_context(
    project: Project | str,
    active_phase: Phase | None = None,
    selected_task: Task | None = None,
    options: StartupContextOptions | None = None,
    startup_task_memory_result: StartupTaskMemoryRetrievalResult | None = None,
    branch: str | None = None,
    is_resuming: bool | None = None,
) -> str:
    """Generate the unified startup context from explicit startup inputs."""
    resolved_options = options or StartupContextOptions()
    resolved_project = project if isinstance(project, Project) else Project.get(project)
    if not resolved_project:
        return "Project not found."

    if isinstance(project, str) and active_phase is None and selected_task is None:
        active_phase, selected_task = _resolve_default_startup_inputs(resolved_project.id)

    sections = [
        "# STARTUP CONTEXT",
        _build_project_frame(resolved_project, resolved_options),
        _build_phase_frame(active_phase, resolved_options),
        _build_task_frame(selected_task, resolved_options, branch=branch, is_resuming=is_resuming),
        _build_guardrail_frame(resolved_project.id, resolved_options),
        _build_task_memory_candidates_frame(
            resolved_project,
            active_phase,
            selected_task,
            resolved_options,
            startup_task_memory_result,
        ),
        _build_next_action(resolved_project, selected_task),
    ]

    rendered = "\n\n".join(sections)
    return _enforce_hard_budget(rendered, resolved_options.hard_char_budget)
