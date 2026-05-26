"""Task service operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from engram.db import get_db_connection
from engram.models.phase import Phase
from engram.models.task import Task
from engram.services.errors import EngramServiceError, ValidationError
from engram.services.serializers import task_to_dict

VALID_TASK_STATUSES = {"todo", "in-progress", "done", "blocked", "cancelled", "all"}
VALID_TASK_UPDATE_FIELDS = {
    "title",
    "status",
    "priority",
    "description",
    "tags",
    "acceptance",
    "phase",
    "phase_id",
    "evidence",
    "depends_on",
    "relevant_files",
}


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


def get_next_task(project_id: str) -> dict[str, object] | None:
    """Return the next actionable task as a JSON-safe DTO, if one exists."""
    next_task = Task.get_next(project_id)
    if next_task is None:
        return None
    return task_to_dict(next_task)


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
    allowed_statuses = VALID_TASK_STATUSES - {"all"}
    if status not in allowed_statuses:
        raise ValidationError(
            code="INVALID_TASK_STATUS",
            message="Task status is invalid.",
            details={"status": status, "allowed_statuses": sorted(allowed_statuses)},
        )

    allowed_priorities = {"critical", "high", "medium", "low"}
    if priority not in allowed_priorities:
        raise ValidationError(
            code="INVALID_TASK_PRIORITY",
            message="Task priority is invalid.",
            details={"priority": priority, "allowed_priorities": sorted(allowed_priorities)},
        )

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


def _check_dependency_cycle(task_id: str, depends_on_id: str | None, project_id: str) -> None:
    """Validate that the dependency edge does not create a cycle."""
    if not depends_on_id:
        return

    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, depends_on FROM tasks WHERE project_id = ?", (project_id,)
    ).fetchall()
    conn.close()

    dep_map = {row["id"]: row["depends_on"] for row in rows}
    dep_map[task_id] = depends_on_id

    visited: set[str] = set()
    path: set[str] = set()

    def dfs(node: str) -> bool:
        if node in path:
            return True
        if node in visited:
            return False

        path.add(node)
        dep = dep_map.get(node)
        if dep:
            if dfs(dep):
                return True
        path.remove(node)
        visited.add(node)
        return False

    if dfs(task_id):
        raise ValidationError(
            code="DEPENDENCY_CYCLE",
            message="Circular dependency detected.",
            details={"task_id": task_id, "depends_on": depends_on_id},
        )


def update_task(
    project_id: str,
    task_ref: str,
    **kwargs: Any,
) -> dict[str, object]:
    """Update a task with validation and return its updated JSON-safe DTO."""
    has_explicit_phase = "phase" in kwargs
    task_id = resolve_task_ref(project_id, task_ref)
    task_item = Task.get(task_id)
    if task_item is None:
        raise EngramServiceError(
            code="TASK_NOT_FOUND",
            message="Task reference was not found in this project.",
            details={"project_id": project_id, "task_ref": task_ref.strip()},
        )

    # Reject unknown fields
    unknown_fields = set(kwargs.keys()) - VALID_TASK_UPDATE_FIELDS
    if unknown_fields:
        raise ValidationError(
            code="UNKNOWN_UPDATE_FIELDS",
            message="Unknown fields in update payload.",
            details={
                "unknown_fields": sorted(list(unknown_fields)),
                "allowed_fields": sorted(list(VALID_TASK_UPDATE_FIELDS)),
            },
        )

    # Validate status
    if "status" in kwargs:
        status = kwargs["status"]
        allowed_statuses = VALID_TASK_STATUSES - {"all"}
        if status not in allowed_statuses:
            raise ValidationError(
                code="INVALID_TASK_STATUS",
                message="Task status is invalid.",
                details={"status": status, "allowed_statuses": sorted(allowed_statuses)},
            )

    # Validate priority
    if "priority" in kwargs:
        priority = kwargs["priority"]
        allowed_priorities = {"critical", "high", "medium", "low"}
        if priority not in allowed_priorities:
            raise ValidationError(
                code="INVALID_TASK_PRIORITY",
                message="Task priority is invalid.",
                details={"priority": priority, "allowed_priorities": sorted(allowed_priorities)},
            )

    # Validate/resolve depends_on
    if "depends_on" in kwargs:
        dep_val = kwargs["depends_on"]
        if dep_val is None or (
            isinstance(dep_val, str) and dep_val.strip().lower() in ("none", "null", "clear", "")
        ):
            kwargs["depends_on"] = None
        else:
            if not isinstance(dep_val, str):
                raise ValidationError(
                    code="INVALID_DEPENDENCY",
                    message="Task dependency must be a string task reference.",
                    details={"depends_on": dep_val},
                )
            try:
                resolved_dep = resolve_task_ref(project_id, dep_val)
            except EngramServiceError as e:
                raise ValidationError(
                    code="TASK_NOT_FOUND",
                    message=e.message,
                    details=e.details,
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
            if not isinstance(p_val, str):
                raise ValidationError(
                    code="INVALID_PHASE_REFERENCE",
                    message="Phase reference must be a string.",
                    details={"phase_id": p_val},
                )
            candidate = p_val.strip()
            if not candidate:
                raise ValidationError(
                    code="INVALID_PHASE_REFERENCE",
                    message="Phase reference cannot be empty.",
                    details={"phase_id": p_val},
                )

            phase = Phase.get(candidate)
            if not (phase and phase.project_id == project_id):
                # Try title match
                normalized_candidate = _normalize_phase_title(candidate)
                matching_phases = [
                    project_phase
                    for project_phase in Phase.list_by_project(project_id)
                    if _normalize_phase_title(project_phase.title) == normalized_candidate
                ]
                if len(matching_phases) == 1:
                    phase = matching_phases[0]
                elif len(matching_phases) > 1:
                    matches = ", ".join(f"{match.id} ({match.title})" for match in matching_phases)
                    raise ValidationError(
                        code="AMBIGUOUS_PHASE",
                        message=f"Ambiguous phase '{candidate}'. Multiple phases match this title: {matches}",
                        details={
                            "phase_ref": candidate,
                            "matches": [m.id for m in matching_phases],
                        },
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
    effective_phase_id = kwargs.get("phase_id", task_item.phase_id)
    if has_explicit_phase and kwargs.get("phase") is not None:
        if effective_phase_id is not None:
            raise ValidationError(
                code="PHASE_LINKED_TO_FIRST_CLASS",
                message="Task is linked to a first-class phase. Use phase_id to change the effective phase, or phase_id=None to clear the link first.",
                details={"task_id": task_id, "phase_id": effective_phase_id},
            )

    # Perform update using Task model method (maintaining audit integrity)
    task_item.update(**kwargs)
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
