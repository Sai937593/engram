"""CRUD operations for tasks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from engram.models.phase import Phase as _Phase
from engram.models.task import Task as _Task
from engram.services.errors import EngramServiceError as _EngramServiceError
from engram.services.errors import ValidationError as _ValidationError
from engram.services.serializers import task_to_dict as _task_to_dict
from engram.services.task.dependency_ref import (
    normalize_dependency_ref as _normalize_dependency_ref,
)
from engram.services.task.update_resolution import (
    validate_and_resolve_update as _validate_and_resolve_update,
)
from engram.services.task.validation import (
    VALID_TASK_STATUSES as _VALID_TASK_STATUSES,
)
from engram.services.task.validation import (
    resolve_task_ref as _resolve_task_ref,
)
from engram.services.task.validation import (
    validate_priority_field as _validate_priority_field,
)
from engram.services.task.validation import (
    validate_status_field as _validate_status_field,
)


class _Helpers:
    @staticmethod
    def normalize_phase_title(title: str | None) -> str:
        """Return a case-insensitive, whitespace-normalized phase key."""
        return "" if title is None else " ".join(title.split()).casefold()

    @staticmethod
    def normalize_status(status: str | None) -> str:
        """Normalize and validate task status filter values."""
        if status is None:
            return "todo"
        normalized = status.strip().casefold()
        if normalized in _VALID_TASK_STATUSES:
            return normalized
        raise _EngramServiceError(
            code="INVALID_TASK_STATUS",
            message="Task status filter is invalid.",
            details={"status": status, "allowed_statuses": sorted(_VALID_TASK_STATUSES)},
        )

    @staticmethod
    def resolve_phase_filter(project_id: str, phase: str | None) -> tuple[str | None, str]:
        """Resolve phase input to first-class and legacy-compatible filter keys."""
        if not phase or not phase.strip():
            return None, ""
        candidate = phase.strip()
        phase_match = _Phase.get(candidate)
        if phase_match and phase_match.project_id == project_id:
            return phase_match.id, _Helpers.normalize_phase_title(phase_match.title)
        normalized_candidate = _Helpers.normalize_phase_title(candidate)
        matching = [
            p
            for p in _Phase.list_by_project(project_id)
            if _Helpers.normalize_phase_title(p.title) == normalized_candidate
        ]
        if len(matching) == 1:
            return matching[0].id, _Helpers.normalize_phase_title(matching[0].title)
        return None, normalized_candidate

    @staticmethod
    def filter_by_phase(tasks: list[_Task], project_id: str, phase: str | None) -> list[_Task]:
        """Filter tasks by phase with first-class semantics and legacy compatibility."""
        resolved_phase_id, normalized_phase = _Helpers.resolve_phase_filter(project_id, phase)
        if not normalized_phase and resolved_phase_id is None:
            return tasks
        filtered: list[_Task] = []
        for t in tasks:
            if resolved_phase_id:
                if t.phase_id == resolved_phase_id or (
                    not t.phase_id and _Helpers.normalize_phase_title(t.phase) == normalized_phase
                ):
                    filtered.append(t)
            elif not t.phase_id and _Helpers.normalize_phase_title(t.phase) == normalized_phase:
                filtered.append(t)
        return filtered


def list_tasks(
    project_id: str, status: str | None = None, phase: str | None = None
) -> list[dict[str, object]]:
    """Return JSON-safe task DTOs filtered by effective status and optional phase."""
    normalized_status = _Helpers.normalize_status(status)
    filtered_tasks = _Helpers.filter_by_phase(_Task.list_by_project(project_id), project_id, phase)
    task_payloads = [_task_to_dict(t) for t in filtered_tasks]
    if normalized_status == "all":
        return task_payloads
    return [t for t in task_payloads if t["effective_status"] == normalized_status]


def get_task(project_id: str, task_ref: str) -> dict[str, object]:
    """Resolve a project-scoped task reference and return a JSON-safe task DTO."""
    task_id = _resolve_task_ref(project_id, task_ref)
    task_item = _Task.get(task_id)
    if task_item is None:
        raise _EngramServiceError(
            code="TASK_NOT_FOUND",
            message="Task reference was not found in this project.",
            details={"project_id": project_id, "task_ref": task_ref.strip()},
        )
    return _task_to_dict(task_item)


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
    _validate_status_field(status)
    _validate_priority_field(priority)
    dep = _normalize_dependency_ref(project_id, depends_on, task_id=id)
    t = _Task.create(
        project_id=project_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        phase=phase,
        phase_id=phase_id,
        depends_on=dep,
        acceptance=acceptance,
        tags=tags,
        relevant_files=relevant_files,
        id=id,
    )
    return _task_to_dict(t)


def update_task(project_id: str, task_ref: str, **kwargs: Any) -> dict[str, object]:
    """Update a task with validation and return its updated JSON-safe DTO."""
    task_id = _resolve_task_ref(project_id, task_ref)
    t = _Task.get(task_id)
    if t is None:
        raise _EngramServiceError(
            code="TASK_NOT_FOUND",
            message="Task reference was not found in this project.",
            details={"project_id": project_id, "task_ref": task_ref.strip()},
        )
    resolved = _validate_and_resolve_update(project_id, task_id, t, **kwargs)
    t.update(**resolved)
    return _task_to_dict(t)


def append_task_note(project_id: str, task_ref: str, note: str) -> dict[str, object]:
    """Append a timestamped note to a task's evidence log with validation."""
    task_id = _resolve_task_ref(project_id, task_ref)
    t = _Task.get(task_id)
    if t is None:
        raise _EngramServiceError(
            code="TASK_NOT_FOUND",
            message="Task reference was not found in this project.",
            details={"project_id": project_id, "task_ref": task_ref.strip()},
        )
    if not note or not note.strip():
        raise _ValidationError(
            code="INVALID_NOTE", message="Task note cannot be empty.", details={"note": note}
        )
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"[{ts}] {note.strip()}"
    updated = (t.evidence + "\n" + entry).strip() if t.evidence else entry
    t.update(evidence=updated)
    return _task_to_dict(t)
