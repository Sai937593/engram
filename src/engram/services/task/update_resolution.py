"""Update payload resolution for task service writes."""

from __future__ import annotations

from typing import Any

from engram.models.phase import Phase
from engram.models.task import Task
from engram.services.errors import ValidationError
from engram.services.task.dependency_ref import normalize_dependency_ref
from engram.services.task.validation import (
    VALID_TASK_UPDATE_FIELDS,
    _normalize_phase_title,
    validate_priority_field,
    validate_status_field,
)


def validate_and_resolve_update(
    project_id: str,
    task_id: str,
    task_item: Task,
    **kwargs: Any,
) -> dict[str, Any]:
    """Validate and resolve all update payload fields, returning resolved update kwargs."""
    has_explicit_phase = "phase" in kwargs

    unknown = set(kwargs) - VALID_TASK_UPDATE_FIELDS
    if unknown:
        raise ValidationError(
            code="UNKNOWN_UPDATE_FIELDS",
            message="Unknown fields in update payload.",
            details={
                "unknown_fields": sorted(unknown),
                "allowed_fields": sorted(VALID_TASK_UPDATE_FIELDS),
            },
        )

    if "status" in kwargs:
        validate_status_field(kwargs["status"])
    if "priority" in kwargs:
        validate_priority_field(kwargs["priority"])
    if "depends_on" in kwargs:
        kwargs["depends_on"] = normalize_dependency_ref(
            project_id, kwargs["depends_on"], task_id=task_id
        )

    if "phase_id" in kwargs:
        _resolve_phase_link(project_id, kwargs)

    eff_phase_id = kwargs.get("phase_id", task_item.phase_id)
    if has_explicit_phase and kwargs.get("phase") is not None and eff_phase_id is not None:
        raise ValidationError(
            code="PHASE_LINKED_TO_FIRST_CLASS",
            message="Task is linked to a first-class phase. Use phase_id to change the effective phase, or phase_id=None to clear the link first.",
            details={"task_id": task_id, "phase_id": eff_phase_id},
        )
    return kwargs


def _resolve_phase_link(project_id: str, kwargs: dict[str, Any]) -> None:
    """Resolve first-class phase reference and synchronize legacy phase title."""
    phase_ref = kwargs["phase_id"]
    if phase_ref is None or (
        isinstance(phase_ref, str) and phase_ref.strip().lower() in ("none", "null", "clear", "")
    ):
        kwargs["phase_id"] = None
        kwargs["phase"] = None
        return
    if not isinstance(phase_ref, str) or not phase_ref.strip():
        raise ValidationError(
            code="INVALID_PHASE_REFERENCE",
            message="Phase reference must be a non-empty string.",
            details={"phase_id": phase_ref},
        )

    candidate = phase_ref.strip()
    phase = Phase.get(candidate)
    if not phase or phase.project_id != project_id:
        normalized = _normalize_phase_title(candidate)
        matching = [
            item
            for item in Phase.list_by_project(project_id)
            if _normalize_phase_title(item.title) == normalized
        ]
        if len(matching) == 1:
            phase = matching[0]
        elif len(matching) > 1:
            matches = ", ".join(f"{item.id} ({item.title})" for item in matching)
            raise ValidationError(
                code="AMBIGUOUS_PHASE",
                message=f"Ambiguous phase '{candidate}'. Multiple phases match: {matches}",
                details={"phase_ref": candidate, "matches": [item.id for item in matching]},
            )
        else:
            raise ValidationError(
                code="PHASE_NOT_FOUND",
                message=f"Phase '{candidate}' not found in this project.",
                details={"project_id": project_id, "phase_ref": candidate},
            )

    kwargs["phase_id"] = phase.id
    kwargs["phase"] = phase.title
