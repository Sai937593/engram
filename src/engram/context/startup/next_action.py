"""Next-action rendering for startup context."""

from __future__ import annotations

from engram.context.startup.options import _render_section
from engram.models.project import Project
from engram.models.task import Task


def build_next_action(project: Project, selected_task: Task | None) -> str:
    """Build the next action instruction section."""
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
