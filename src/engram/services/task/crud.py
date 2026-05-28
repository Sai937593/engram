"""CRUD operations for tasks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from engram.models.phase import Phase
from engram.models.task import Task
from engram.services.errors import EngramServiceError, ValidationError
from engram.services.serializers import task_to_dict
from engram.services.task.validation import (
    VALID_TASK_UPDATE_FIELDS,
    _check_dependency_cycle,
    _filter_by_phase,
    _normalize_phase_title,
    _normalize_status,
    resolve_task_ref,
    validate_priority_field,
    validate_status_field,
)


def list_tasks(
    project_id: str, status: str | None = None, phase: str | None = None
) -> list[dict[str, object]]:
    """Return JSON-safe task DTOs filtered by effective status and optional phase."""
    normalized_status = _normalize_status(status)
    filtered_tasks = _filter_by_phase(Task.list_by_project(project_id), project_id, phase)
    task_payloads = [task_to_dict(task_item) for task_item in filtered_tasks]

    if normalized_status == "all":
        return task_payloads

    return [
        task_payload
        for task_payload in task_payloads
        if task_payload["effective_status"] == normalized_status
    ]


def get_task(project_id: str, task_ref: str) -> dict[str, object]:
    """Resolve a project-scoped task reference and return a JSON-safe task DTO."""
    task_id = resolve_task_ref(project_id, task_ref)
    task_item = Task.get(task_id)
    if task_item is None:
        raise EngramServiceError(
            code="TASK_NOT_FOUND",
            message="Task reference was not found in this project.",
            details={"project_id": project_id, "task_ref": task_ref.strip()},
        )
    return task_to_dict(task_item)


def create_task(
    project_id: str,
    title: str,
    description: str | None = None,
    status: str = "todo",
    priority: str = "medium",
    phase: str | None = None,
    phase_id: str | None = None,
    depends_on: str | None = None,
    acceptance: str | None = None,
    tags: list[str] | None = None,
    relevant_files: list[str] | None = None,
    id: str | None = None,
) -> dict[str, object]:
    """Create a new task with validation and return its JSON-safe DTO."""
    validate_status_field(status)
    validate_priority_field(priority)

    task_item = Task.create(
        project_id=project_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        phase=phase,
        phase_id=phase_id,
        depends_on=depends_on,
        acceptance=acceptance,
        tags=tags,
        relevant_files=relevant_files,
        id=id,
    )
    return task_to_dict(task_item)


def validate_and_resolve_update(
    project_id: str,
    task_id: str,
    task_item: Task,
    **kwargs: Any,
) -> dict[str, Any]:
    """Validate and resolve all update payload fields, returning resolved update kwargs."""
    has_explicit_phase = "phase" in kwargs

    # Reject unknown fields
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

    # Validate status and priority
    if "status" in kwargs:
        validate_status_field(kwargs["status"])
    if "priority" in kwargs:
        validate_priority_field(kwargs["priority"])

    # Validate/resolve depends_on
    if "depends_on" in kwargs:
        dep = kwargs["depends_on"]
        if dep is None or (
            isinstance(dep, str) and dep.strip().lower() in ("none", "null", "clear", "")
        ):
            kwargs["depends_on"] = None
        else:
            if not isinstance(dep, str):
                raise ValidationError(
                    code="INVALID_DEPENDENCY",
                    message="Task dependency must be a string task reference.",
                    details={"depends_on": dep},
                )
            try:
                resolved_dep = resolve_task_ref(project_id, dep)
            except EngramServiceError as e:
                raise ValidationError(
                    code="TASK_NOT_FOUND", message=e.message, details=e.details
                ) from e
            if resolved_dep == task_id:
                raise ValidationError(
                    code="DEPENDENCY_CYCLE",
                    message="A task cannot depend on itself.",
                    details={"task_id": task_id, "depends_on": resolved_dep},
                )
            _check_dependency_cycle(task_id, resolved_dep, project_id)
            kwargs["depends_on"] = resolved_dep

    # Validate/resolve phase_id and phase
    if "phase_id" in kwargs:
        p_val = kwargs["phase_id"]
        if p_val is None or (
            isinstance(p_val, str) and p_val.strip().lower() in ("none", "null", "clear", "")
        ):
            kwargs["phase_id"] = None
            kwargs["phase"] = None
        else:
            if not isinstance(p_val, str) or not p_val.strip():
                raise ValidationError(
                    code="INVALID_PHASE_REFERENCE",
                    message="Phase reference must be a non-empty string.",
                    details={"phase_id": p_val},
                )
            candidate = p_val.strip()
            phase = Phase.get(candidate)
            if not phase or phase.project_id != project_id:
                normalized = _normalize_phase_title(candidate)
                matching = [
                    p
                    for p in Phase.list_by_project(project_id)
                    if _normalize_phase_title(p.title) == normalized
                ]
                if len(matching) == 1:
                    phase = matching[0]
                elif len(matching) > 1:
                    matches = ", ".join(f"{m.id} ({m.title})" for m in matching)
                    raise ValidationError(
                        code="AMBIGUOUS_PHASE",
                        message=f"Ambiguous phase '{candidate}'. Multiple phases match: {matches}",
                        details={"phase_ref": candidate, "matches": [m.id for m in matching]},
                    )
                else:
                    raise ValidationError(
                        code="PHASE_NOT_FOUND",
                        message=f"Phase '{candidate}' not found in this project.",
                        details={"project_id": project_id, "phase_ref": candidate},
                    )
            kwargs["phase_id"] = phase.id
            kwargs["phase"] = phase.title

    # Enforce first-class phase link check when legacy phase title is provided
    eff_phase_id = kwargs.get("phase_id", task_item.phase_id)
    if has_explicit_phase and kwargs.get("phase") is not None and eff_phase_id is not None:
        raise ValidationError(
            code="PHASE_LINKED_TO_FIRST_CLASS",
            message="Task is linked to a first-class phase. Use phase_id to change the effective phase, or phase_id=None to clear the link first.",
            details={"task_id": task_id, "phase_id": eff_phase_id},
        )

    return kwargs


def update_task(
    project_id: str,
    task_ref: str,
    **kwargs: Any,
) -> dict[str, object]:
    """Update a task with validation and return its updated JSON-safe DTO."""
    task_id = resolve_task_ref(project_id, task_ref)
    task_item = Task.get(task_id)
    if task_item is None:
        raise EngramServiceError(
            code="TASK_NOT_FOUND",
            message="Task reference was not found in this project.",
            details={"project_id": project_id, "task_ref": task_ref.strip()},
        )

    resolved_kwargs = validate_and_resolve_update(project_id, task_id, task_item, **kwargs)
    task_item.update(**resolved_kwargs)
    return task_to_dict(task_item)


def append_task_note(
    project_id: str,
    task_ref: str,
    note: str,
) -> dict[str, object]:
    """Append a timestamped note to a task's evidence log with validation."""
    task_id = resolve_task_ref(project_id, task_ref)
    task_item = Task.get(task_id)
    if task_item is None:
        raise EngramServiceError(
            code="TASK_NOT_FOUND",
            message="Task reference was not found in this project.",
            details={"project_id": project_id, "task_ref": task_ref.strip()},
        )

    if not note or not note.strip():
        raise ValidationError(
            code="INVALID_NOTE",
            message="Task note cannot be empty.",
            details={"note": note},
        )

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"[{timestamp}] {note.strip()}"
    existing = task_item.evidence or ""
    updated = (existing + "\n" + new_entry).strip() if existing else new_entry

    task_item.update(evidence=updated)
    return task_to_dict(task_item)
