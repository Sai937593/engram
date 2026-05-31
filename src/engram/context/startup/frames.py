"""Legacy frame builders for startup context sections."""

from __future__ import annotations

from engram.context.startup.options import (
    StartupContextOptions,
    _compact_with_limit,
    _render_section,
)
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task, get_effective_phase_title


def _build_project_frame(project: Project, options: StartupContextOptions) -> str:
    """Build the project frame section."""
    lines = [f"Name: {project.name}"]
    summary = _compact_with_limit(project.summary, options.project_summary_char_limit)
    if summary:
        lines.append(f"Summary: {summary}")
    return _render_section("PROJECT FRAME", lines)


def _build_phase_frame(active_phase: Phase | None, options: StartupContextOptions) -> str:
    """Build the current phase frame section."""
    if not active_phase:
        return _render_section("CURRENT PHASE FRAME", ["No active phase selected."])
    lines = [f"Phase: {active_phase.title} ({active_phase.id})", f"Status: {active_phase.status}"]
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
    """Build the current or next task frame section."""
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
        lines.extend(["", "Relevant files:"])
        capped_paths = selected_task.relevant_files[: options.relevant_file_limit]
        for path in capped_paths:
            if compact_path := _compact_with_limit(path, options.relevant_file_path_char_limit):
                lines.append(f"- {compact_path}")
        hidden_path_count = max(0, len(selected_task.relevant_files) - len(capped_paths))
        if hidden_path_count:
            lines.append(f"... {hidden_path_count} additional relevant file path(s) hidden by cap.")
    return _render_section("CURRENT/NEXT TASK FRAME", lines)
