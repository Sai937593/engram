"""Section frame builders for engram startup context."""

from __future__ import annotations

from engram.context.startup.options import (
    StartupContextOptions,
    _compact_with_limit,
    _render_section,
)
from engram.hooks.py_structure import L1_GUARDRAIL_RULES
from engram.memory_retrieval import (
    StartupTaskMemoryRetrievalResult,
    orchestrate_startup_task_memory_retrieval,
)
from engram.models.memory import Memory
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task


def _build_guardrail_frame(project_id: str, options: StartupContextOptions) -> str:
    """Build the project guardrails section."""
    guardrails = Memory.list_project_guardrail_candidates(project_id)
    l0_guardrails = sorted(
        [m for m in guardrails if m.level == "L0"], key=lambda m: (m.title, m.id)
    )
    l1_guardrails = sorted(
        [m for m in guardrails if m.level == "L1"], key=lambda m: (m.title, m.id)
    )
    py_structure_l1 = L1_GUARDRAIL_RULES
    capped_l1 = l1_guardrails[: options.l1_guardrail_limit]
    hidden_l1_count = max(0, len(l1_guardrails) - len(capped_l1))

    lines: list[str] = []
    if not l0_guardrails and not capped_l1 and not py_structure_l1:
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
    elif py_structure_l1:
        lines.append("L1 Constraints:")

    for title, content_raw in py_structure_l1:
        content = _compact_with_limit(content_raw, options.guardrail_text_char_limit)
        lines.append(f"- {title}: {content}")

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
    """Build the task memory candidates section."""
    result = retrieval_result or orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=active_phase,
        selected_task=selected_task,
    )
    lines: list[str] = []
    packed_items = result.pack_result.items

    if not packed_items:
        empty_state = _compact_with_limit(
            options.task_memory_empty_state_text, options.task_memory_empty_state_char_limit
        )
        if empty_state:
            lines.append(empty_state)
        if selected_task:
            lines.append("Search next using engram_memory_search with:")
            search_hints: list[str] = []
            title_hint = _compact_with_limit(
                selected_task.title, options.task_memory_search_hint_char_limit
            )
            if title_hint:
                search_hints.append(title_hint)
            if active_phase and (
                phase_hint := _compact_with_limit(
                    active_phase.title, options.task_memory_search_hint_char_limit
                )
            ):
                search_hints.append(phase_hint)
            if selected_task.tags:
                search_hints.extend(
                    compact_tag
                    for tag in selected_task.tags
                    if (
                        compact_tag := _compact_with_limit(
                            tag, options.task_memory_search_hint_char_limit
                        )
                    )
                )
            for hint in search_hints[: options.task_memory_search_hint_limit]:
                lines.append(f"- {hint}")
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
