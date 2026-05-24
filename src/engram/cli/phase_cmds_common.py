"""Shared helpers/constants for phase CLI commands."""

import engram.cli as cli_root
from engram.cli.phase_helpers import normalize_phase_title
from engram.models.phase import Phase
from engram.models.task import Task

VALID_PHASE_FIELDS = {"title", "description", "status", "order_index", "acceptance", "evidence"}
VALID_PHASE_STATUSES = {"planned", "active", "done", "blocked", "cancelled"}


def print_demoted_phase_count(demoted_count: int) -> None:
    """Print a summary when activation demotes existing active phases."""
    if not demoted_count:
        return

    noun = "phase" if demoted_count == 1 else "phases"
    cli_root.console.print(
        f"[yellow]Demoted {demoted_count} previously active {noun} to planned.[/yellow]"
    )


def compact_phase_summary(phase: Phase) -> str:
    """Return compact one-line summary text for phase list rows."""
    summary_source = phase.description or phase.acceptance
    if not summary_source:
        return "-"

    return " ".join(summary_source.split())


def task_is_linked_to_phase(task: Task, phase: Phase) -> bool:
    """Return whether a task is linked via phase_id or legacy phase title."""
    if task.phase_id == phase.id:
        return True
    if task.phase_id:
        return False
    return normalize_phase_title(task.phase) == normalize_phase_title(phase.title)


def unfinished_linked_task_ids(project_id: str, phase: Phase) -> list[str]:
    """Return unfinished task IDs linked to a phase in the current project."""
    blocking_statuses = {"todo", "in-progress", "blocked"}
    linked_blockers: list[str] = []

    for task in Task.list_by_project(project_id):
        if task.status not in blocking_statuses:
            continue
        if task_is_linked_to_phase(task, phase):
            linked_blockers.append(task.id)

    return sorted(linked_blockers)
