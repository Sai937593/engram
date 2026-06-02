"""Compact formatter for the workflow start work order."""

from __future__ import annotations

from engram.context.common import compact_text
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task


def _compact_line(text: str | None, limit: int = 220) -> str:
    """Return one compact ASCII line suitable for workflow output."""
    cleaned = compact_text(text).replace("\r", " ").replace("\n", " ").strip()
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    if limit <= 3:
        return cleaned[:limit]
    return cleaned[: limit - 3].rstrip() + "..."


def format_start_work_order(
    *,
    branch: str | None,
    task_id: str,
    task_key: str | None,
    task_title: str,
    phase_id: str | None,
    phase_key: str | None,
    phase_title: str | None,
    plan_key: str,
    objective: str | None,
    acceptance: str | None,
    relevant_files: list[str] | None,
    search_hints: list[str] | None,
    verification: str | None,
    task_plan_path: str | None,
    next_action: str,
) -> str:
    """Format the compact Work Order returned by engram_workflow_start."""
    lines = ["# Work Order", ""]
    if branch:
        lines.append(f"Branch: `{branch}`")
        lines.append("")

    lines.append("## Task context")
    task_line = f"- Task: `{task_title}` (`{task_id}`)"
    if task_key and task_key != task_id:
        task_line += f" [key: `{task_key}`]"
    lines.append(task_line)
    if phase_title or phase_id or phase_key:
        phase_line = "- Phase: "
        if phase_title:
            phase_line += f"`{phase_title}`"
        if phase_id:
            phase_line += f" (`{phase_id}`)"
        if phase_key and phase_key != phase_id:
            phase_line += f" [key: `{phase_key}`]"
        lines.append(phase_line)
    lines.append(f"- Plan: `{plan_key}`")
    lines.append("")

    lines.append("## Objective")
    lines.append(_compact_line(objective) or "No objective recorded.")
    lines.append("")

    lines.append("## Acceptance")
    lines.append(_compact_line(acceptance) or "No acceptance recorded.")
    lines.append("")

    lines.append("## Start here")
    if relevant_files:
        capped_files = relevant_files[:5]
        for path in capped_files:
            compact_path = _compact_line(path, 160)
            if compact_path:
                lines.append(f"- {compact_path}")
        hidden_count = max(0, len(relevant_files) - len(capped_files))
        if hidden_count:
            lines.append(f"- ... {hidden_count} additional relevant file path(s) hidden by cap.")
    else:
        lines.append(
            "- Search the codebase using the task title and phase title if you need more context."
        )
        if search_hints:
            for hint in search_hints[:3]:
                compact_hint = _compact_line(hint, 80)
                if compact_hint:
                    lines.append(f"- Search hint: {compact_hint}")
    lines.append("")

    lines.append("## Verification")
    lines.append(
        _compact_line(verification) or "- Run `engram_workflow_verify` after implementation."
    )
    lines.append("")

    lines.append("## Required task plan")
    if task_plan_path:
        lines.append(f"- Create `{task_plan_path}` before coding.")
    else:
        lines.append(
            "- Create `.engram/task-plans/<plan_key>/<phase_key>/<task_key>/task-plan.md` before coding."
        )
    lines.append("")

    lines.append("## Next action")
    lines.append(
        _compact_line(next_action) or "- Implement the task and rerun verification when ready."
    )
    lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_start_work_order(
    project: Project,
    active_phase: Phase | None,
    task: Task,
    branch: str,
    is_resuming: bool | None = None,
) -> str:
    """Build the compact work order for the active start-workflow task."""
    relevant_files = [path for path in task.relevant_files[:5] if path]
    search_hints: list[str] | None = None
    if not relevant_files:
        search_hints = [
            hint for hint in [task.title, active_phase.title if active_phase else None] if hint
        ]
        if task.tags:
            search_hints.append(", ".join(task.tags[:3]))

    phase_key = active_phase.key if active_phase else task.phase_id
    task_plan_path = (
        f".engram/task-plans/{project.plan_key}/{phase_key}/{task.key}/task-plan.md"
        if phase_key
        else None
    )
    next_action = (
        f"If deeper context is needed: engram_task_get {task.id}. "
        "Otherwise implement the task and rerun engram_workflow_verify when ready."
    )
    if is_resuming:
        next_action = (
            f"Resume the task using the work order above. If deeper context is needed: "
            f"engram_task_get {task.id}. Otherwise implement the task and rerun "
            "engram_workflow_verify when ready."
        )

    return format_start_work_order(
        branch=branch,
        task_id=task.id,
        task_key=task.key,
        task_title=task.title,
        phase_id=active_phase.id if active_phase else task.phase_id,
        phase_key=phase_key,
        phase_title=active_phase.title if active_phase else task.phase,
        plan_key=project.plan_key,
        objective=task.description,
        acceptance=task.acceptance,
        relevant_files=relevant_files or None,
        search_hints=search_hints,
        verification=task.verification,
        task_plan_path=task_plan_path,
        next_action=next_action,
    )
