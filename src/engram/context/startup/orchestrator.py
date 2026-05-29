"""Orchestrator for assembling engram startup context."""

from __future__ import annotations

from engram.context.common import compact_text
from engram.context.startup.builders import (
    _build_guardrail_frame,
    _build_next_action,
    _build_phase_frame,
    _build_project_frame,
    _build_task_frame,
    _build_task_memory_candidates_frame,
)
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
