"""Orchestrator for assembling engram startup context."""

from __future__ import annotations

from engram.context.common import compact_text
from engram.context.startup.builders import (
    _build_guardrail_frame,
    _build_task_memory_candidates_frame,
)
from engram.context.startup.next_action import build_next_action as _build_next_action
from engram.context.startup.options import (
    StartupContextOptions,
    _enforce_hard_budget,
)
from engram.memory_retrieval import StartupTaskMemoryRetrievalResult
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task


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

    from engram.context.startup.options import _compact_with_limit
    from engram.services.workflow_formatter import format_work_order

    # Status
    status = "no-task"
    if selected_task:
        task_slot = "current" if selected_task.status == "in-progress" else "next"
        status = "resuming" if is_resuming else "starting" if is_resuming is not None else task_slot

    # Task properties
    task_id = selected_task.id if selected_task else None
    task_title = selected_task.title if selected_task else None

    # Phase properties
    phase_title = active_phase.title if active_phase else None
    phase_id = active_phase.id if active_phase else None

    # Objective
    if selected_task:
        objective = _compact_with_limit(
            selected_task.description, resolved_options.task_text_char_limit
        )
    else:
        objective = f"No current or next task selected.\nProject: {resolved_project.name}"
        proj_summary = _compact_with_limit(
            resolved_project.summary, resolved_options.project_summary_char_limit
        )
        if proj_summary:
            objective += f" — {proj_summary}"

    # Acceptance
    acceptance = (
        _compact_with_limit(selected_task.acceptance, resolved_options.task_text_char_limit)
        if selected_task
        else None
    )

    # Start here / relevant files
    relevant_files_list = []
    if selected_task and selected_task.relevant_files:
        capped_paths = selected_task.relevant_files[: resolved_options.relevant_file_limit]
        for path in capped_paths:
            compact_path = _compact_with_limit(path, resolved_options.relevant_file_path_char_limit)
            if compact_path:
                relevant_files_list.append(compact_path)
        hidden_path_count = max(0, len(selected_task.relevant_files) - len(capped_paths))
        if hidden_path_count:
            relevant_files_list.append(
                f"... {hidden_path_count} additional relevant file path(s) hidden by cap."
            )

    # Guardrails
    guardrail_str = _build_guardrail_frame(resolved_project.id, resolved_options)
    guardrails_list = [line for line in guardrail_str.split("\n")[1:] if line.strip()]

    # Memories
    memory_str = _build_task_memory_candidates_frame(
        resolved_project,
        active_phase,
        selected_task,
        resolved_options,
        startup_task_memory_result,
    )
    memories_list = [line for line in memory_str.split("\n")[1:] if line.strip()]

    # Next action
    next_action_str = _build_next_action(resolved_project, selected_task)
    next_action_lines = [line for line in next_action_str.split("\n")[1:] if line.strip()]
    next_action_content = "\n".join(next_action_lines)

    rendered = format_work_order(
        status=status,
        task_id=task_id,
        task_title=task_title,
        phase_title=phase_title,
        phase_id=phase_id,
        branch=branch,
        objective=objective,
        acceptance=acceptance,
        relevant_files=relevant_files_list or None,
        guardrails=guardrails_list or None,
        memories=memories_list or None,
        next_action=next_action_content or None,
    )

    return _enforce_hard_budget(rendered, resolved_options.hard_char_budget)
