"""Task service read operations."""

from __future__ import annotations

from engram.db import get_db_connection
from engram.models.phase import Phase
from engram.models.task import Task
from engram.services.errors import EngramServiceError
from engram.services.serializers import task_to_dict

VALID_TASK_STATUSES = {"todo", "in-progress", "done", "blocked", "cancelled", "all"}


def _normalize_phase_title(title: str | None) -> str:
    """Return a case-insensitive, whitespace-normalized phase key."""
    if title is None:
        return ""
    return " ".join(title.split()).casefold()


def _normalize_status(status: str | None) -> str:
    """Normalize and validate task status filter values."""
    if status is None:
        return "todo"

    normalized = status.strip().casefold()
    if normalized in VALID_TASK_STATUSES:
        return normalized

    raise EngramServiceError(
        code="INVALID_TASK_STATUS",
        message="Task status filter is invalid.",
        details={"status": status, "allowed_statuses": sorted(VALID_TASK_STATUSES)},
    )


def _resolve_phase_filter(project_id: str, phase: str | None) -> tuple[str | None, str]:
    """Resolve phase input to first-class and legacy-compatible filter keys."""
    if phase is None:
        return None, ""

    candidate = phase.strip()
    if not candidate:
        return None, ""

    phase_match = Phase.get(candidate)
    if phase_match and phase_match.project_id == project_id:
        return phase_match.id, _normalize_phase_title(phase_match.title)

    normalized_candidate = _normalize_phase_title(candidate)
    matching = [
        project_phase
        for project_phase in Phase.list_by_project(project_id)
        if _normalize_phase_title(project_phase.title) == normalized_candidate
    ]

    if len(matching) == 1:
        resolved = matching[0]
        return resolved.id, _normalize_phase_title(resolved.title)

    return None, normalized_candidate


def _filter_by_phase(tasks: list[Task], project_id: str, phase: str | None) -> list[Task]:
    """Filter tasks by phase with first-class semantics and legacy compatibility."""
    resolved_phase_id, normalized_phase = _resolve_phase_filter(project_id, phase)
    if not normalized_phase and resolved_phase_id is None:
        return tasks

    filtered: list[Task] = []
    for task_item in tasks:
        if resolved_phase_id:
            if task_item.phase_id == resolved_phase_id:
                filtered.append(task_item)
            elif (
                not task_item.phase_id
                and _normalize_phase_title(task_item.phase) == normalized_phase
            ):
                filtered.append(task_item)
            continue

        if not task_item.phase_id and _normalize_phase_title(task_item.phase) == normalized_phase:
            filtered.append(task_item)

    return filtered


def resolve_task_ref(project_id: str, task_ref: str) -> str:
    """Resolve a project-scoped task reference to a single task ID."""
    normalized_ref = task_ref.strip()

    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id FROM tasks WHERE project_id = ? AND (id = ? OR id LIKE ?)",
        (project_id, normalized_ref, normalized_ref + "%"),
    ).fetchall()
    conn.close()

    matching_ids = sorted({str(row["id"]) for row in rows})

    if not matching_ids:
        raise EngramServiceError(
            code="TASK_NOT_FOUND",
            message="Task reference was not found in this project.",
            details={"project_id": project_id, "task_ref": normalized_ref},
        )

    if len(matching_ids) > 1:
        if normalized_ref in matching_ids:
            return normalized_ref
        raise EngramServiceError(
            code="TASK_AMBIGUOUS",
            message="Task reference is ambiguous in this project.",
            details={
                "project_id": project_id,
                "task_ref": normalized_ref,
                "matches": matching_ids,
            },
        )

    return matching_ids[0]


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
