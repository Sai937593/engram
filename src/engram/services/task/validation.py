"""Task validation helpers and constants."""

from __future__ import annotations

from engram.db import get_db_connection
from engram.models.phase import Phase
from engram.models.task import Task
from engram.services.errors import EngramServiceError, ValidationError

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
    if not phase or not phase.strip():
        return None, ""

    candidate = phase.strip()
    phase_match = Phase.get(candidate)
    if phase_match and phase_match.project_id == project_id:
        return phase_match.id, _normalize_phase_title(phase_match.title)

    normalized_candidate = _normalize_phase_title(candidate)
    matching = [
        p
        for p in Phase.list_by_project(project_id)
        if _normalize_phase_title(p.title) == normalized_candidate
    ]

    if len(matching) == 1:
        return matching[0].id, _normalize_phase_title(matching[0].title)

    return None, normalized_candidate


def _filter_by_phase(tasks: list[Task], project_id: str, phase: str | None) -> list[Task]:
    """Filter tasks by phase with first-class semantics and legacy compatibility."""
    resolved_phase_id, normalized_phase = _resolve_phase_filter(project_id, phase)
    if not normalized_phase and resolved_phase_id is None:
        return tasks

    filtered: list[Task] = []
    for t in tasks:
        if resolved_phase_id:
            if t.phase_id == resolved_phase_id or (
                not t.phase_id and _normalize_phase_title(t.phase) == normalized_phase
            ):
                filtered.append(t)
        elif not t.phase_id and _normalize_phase_title(t.phase) == normalized_phase:
            filtered.append(t)

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
        if dep and dfs(dep):
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


def validate_status_field(status: str) -> None:
    """Validate that a task status is valid (excluding 'all')."""
    allowed = VALID_TASK_STATUSES - {"all"}
    if status not in allowed:
        raise ValidationError(
            code="INVALID_TASK_STATUS",
            message="Task status is invalid.",
            details={"status": status, "allowed_statuses": sorted(allowed)},
        )


def validate_priority_field(priority: str) -> None:
    """Validate that a task priority is valid."""
    allowed = {"critical", "high", "medium", "low"}
    if priority not in allowed:
        raise ValidationError(
            code="INVALID_TASK_PRIORITY",
            message="Task priority is invalid.",
            details={"priority": priority, "allowed_priorities": sorted(allowed)},
        )
