"""CRUD operations for tasks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from engram.models.task import Task
from engram.services.errors import EngramServiceError, ValidationError
from engram.services.serializers import task_to_dict
from engram.services.task.dependency_ref import normalize_dependency_ref
from engram.services.task.update_resolution import validate_and_resolve_update
from engram.services.task.validation import (
    _filter_by_phase,
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
    resolved_depends_on = normalize_dependency_ref(project_id, depends_on, task_id=id)

    task_item = Task.create(
        project_id=project_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        phase=phase,
        phase_id=phase_id,
        depends_on=resolved_depends_on,
        acceptance=acceptance,
        tags=tags,
        relevant_files=relevant_files,
        id=id,
    )
    return task_to_dict(task_item)


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
