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
    validate_executable_task_metadata as _validate_executable_task_metadata,
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
            return "open"
        normalized = status.strip().casefold()
        if normalized in {"draft", "ready", "todo"}:
            normalized = "open"
        elif normalized == "in-progress":
            normalized = "in_progress"

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

    @staticmethod
    def normalize_create_inputs(payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize create-task payload aliases and status variants."""
        normalized = dict(payload)
        if normalized.get("description") is None:
            normalized["description"] = normalized.get("objective")
        status = normalized.get("status", "open")
        if status in {"draft", "ready", "todo"}:
            normalized["status"] = "open"
        elif status == "in-progress":
            normalized["status"] = "in_progress"
        else:
            normalized["status"] = status
        return normalized

    @staticmethod
    def validate_create_inputs(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Validate and resolve a normalized create-task payload without writing."""
        _validate_executable_task_metadata(
            title=payload.get("title"),
            description=payload.get("description"),
            acceptance=payload.get("acceptance"),
            phase_id=payload.get("phase_id"),
            verification=payload.get("verification"),
            relevant_files=payload.get("relevant_files"),
            search_hints=payload.get("search_hints"),
        )
        _validate_status_field(payload.get("status", "open"))
        _validate_priority_field(payload.get("priority", "medium"))
        resolved = dict(payload)
        resolved["depends_on"] = _normalize_dependency_ref(
            project_id, payload.get("depends_on"), task_id=payload.get("id")
        )
        return resolved


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
    status: str = "open",
    priority: str = "medium",
    phase: str | None = None,
    phase_id: str | None = None,
    depends_on: str | None = None,
    acceptance: str | None = None,
    tags: list[str] | None = None,
    relevant_files: list[str] | None = None,
    id: str | None = None,
    verification: str | None = None,
    search_hints: list[str] | None = None,
    objective: str | None = None,
) -> dict[str, object]:
    normalized = _Helpers.normalize_create_inputs(
        {
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "phase": phase,
            "phase_id": phase_id,
            "depends_on": depends_on,
            "acceptance": acceptance,
            "tags": tags,
            "relevant_files": relevant_files,
            "id": id,
            "verification": verification,
            "search_hints": search_hints,
            "objective": objective,
        }
    )
    validated = _Helpers.validate_create_inputs(project_id, normalized)
    t = _Task.create(
        project_id=project_id,
        title=validated["title"],
        description=validated.get("description"),
        status=validated.get("status", "open"),
        priority=validated.get("priority", "medium"),
        phase=validated.get("phase"),
        phase_id=validated.get("phase_id"),
        depends_on=validated.get("depends_on"),
        acceptance=validated.get("acceptance"),
        tags=validated.get("tags"),
        relevant_files=validated.get("relevant_files"),
        id=validated.get("id"),
        verification=validated.get("verification"),
        search_hints=validated.get("search_hints"),
    )
    return _task_to_dict(t)


def create_many_tasks(
    project_id: str, task_payloads: list[dict[str, Any]]
) -> list[dict[str, object]]:
    """Create multiple tasks atomically after full batch validation."""
    validated_payloads: list[dict[str, Any]] = []
    errors: list[dict[str, object]] = []

    for index, raw_payload in enumerate(task_payloads):
        try:
            normalized = _Helpers.normalize_create_inputs(raw_payload)
            validated_payloads.append(_Helpers.validate_create_inputs(project_id, normalized))
        except (_ValidationError, _EngramServiceError) as exc:
            errors.append(
                {
                    "index": index,
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": exc.details,
                    },
                }
            )

    if errors:
        raise _ValidationError(
            code="TASK_BATCH_VALIDATION_FAILED",
            message="One or more task payloads failed validation.",
            details={"errors": errors, "count": len(errors)},
        )

    created = _Task.create_many(project_id=project_id, payloads=validated_payloads)
    return [_task_to_dict(task_item) for task_item in created]


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


def record_memory_review_outcome(
    project_id: str,
    task_ref: str,
    outcome: str | None,
) -> dict[str, object]:
    """Record a memory review outcome for a task with validation."""
    return update_task(project_id, task_ref, memory_review_outcome=outcome)
