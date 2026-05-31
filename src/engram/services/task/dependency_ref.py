"""Dependency reference normalization for task services."""

from __future__ import annotations

from engram.services.errors import EngramServiceError, ValidationError
from engram.services.task.validation import _check_dependency_cycle, resolve_task_ref


def normalize_dependency_ref(
    project_id: str,
    depends_on: object,
    *,
    task_id: str | None = None,
) -> str | None:
    """Normalize dependency input into a canonical task ID or None."""
    if depends_on is None or (
        isinstance(depends_on, str) and depends_on.strip().lower() in ("none", "null", "clear", "")
    ):
        return None
    if not isinstance(depends_on, str):
        raise ValidationError(
            code="INVALID_DEPENDENCY",
            message="Task dependency must be a string task reference.",
            details={"depends_on": depends_on},
        )

    try:
        resolved_dep = resolve_task_ref(project_id, depends_on)
    except EngramServiceError as e:
        raise ValidationError(code="TASK_NOT_FOUND", message=e.message, details=e.details) from e

    if task_id and resolved_dep == task_id:
        raise ValidationError(
            code="DEPENDENCY_CYCLE",
            message="A task cannot depend on itself.",
            details={"task_id": task_id, "depends_on": resolved_dep},
        )

    if task_id:
        _check_dependency_cycle(task_id, resolved_dep, project_id)

    return resolved_dep
