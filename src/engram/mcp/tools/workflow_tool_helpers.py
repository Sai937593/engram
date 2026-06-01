"""Helper utilities for workflow MCP tool handlers."""

from __future__ import annotations

from engram.models.task import Task
from engram.services.workflow_formatter import format_finish_blocked

VERIFICATION_GATE_ERROR_CODES = {
    "VERIFICATION_MISSING",
    "VERIFICATION_FAILED",
    "VERIFICATION_INVALID_STATUS",
    "VERIFICATION_STALE_RELEVANT_CHANGES",
}

FINISH_GATE_ERROR_CODES = VERIFICATION_GATE_ERROR_CODES | {
    "TASK_NOT_VERIFIED",
    "WORKTREE_HAS_UNSTAGED_CHANGES",
    "WORKTREE_HAS_UNTRACKED_FILES",
}


def format_verification_finish_blocked(
    project_id: str, reason: str, code: str | None = None
) -> str:
    """Format blocked finish guidance for finish-gated failures."""
    in_progress = [t for t in Task.list_by_project(project_id) if t.status == "in-progress"]
    active_task = in_progress[0] if in_progress else None
    next_guidance = (
        "Run or rerun engram_workflow_verify, then call engram_workflow_finish_and_commit again."
    )
    if code == "TASK_NOT_VERIFIED":
        next_guidance = (
            "Run engram_workflow_verify, then call engram_workflow_finish_and_commit again."
        )
    if code in {"WORKTREE_HAS_UNSTAGED_CHANGES", "WORKTREE_HAS_UNTRACKED_FILES"}:
        next_guidance = (
            "Stage all intended changes and ensure no untracked files remain, "
            "then call engram_workflow_finish_and_commit again."
        )

    return format_finish_blocked(
        task_id=active_task.id if active_task else "unknown",
        task_title=active_task.title if active_task else None,
        reason=reason,
        next_guidance=next_guidance,
    )
