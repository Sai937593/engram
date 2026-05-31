"""Unified agent and task context generation."""

from engram.context.common import compact_text

__all__ = [
    "_compact_text",
    "get_handoff_context",
    "get_snapshot_context",
    "get_startup_context",
    "get_task_context",
]


def _compact_text(text: str | None) -> str:
    """Safely convert text to ASCII without truncation."""
    return compact_text(text)


def get_startup_context(project_id: str) -> str:
    """Generate a compact, agent-optimized startup context string."""
    # Import lazily so leaf helpers like `engram.context.common` do not pull the
    # startup builder graph back into partially initialized packages.
    from engram.context.startup.orchestrator import build_startup_context

    return build_startup_context(project_id)


def get_task_context(task_id: str, hard_constraints_only: bool = False) -> str:
    """Generate focused context for a specific task."""
    from engram.context.task import build_task_context

    return build_task_context(task_id, hard_constraints_only=hard_constraints_only)


def get_snapshot_context(project_id: str) -> str:
    """Export a full project snapshot as agent-readable Markdown."""
    from engram.context.snapshot import build_snapshot_context

    return build_snapshot_context(project_id)


def get_handoff_context(project_id: str) -> str:
    """Generate a project handoff document for another agent or human."""
    from engram.context.handoff import build_handoff_context

    return build_handoff_context(project_id)
