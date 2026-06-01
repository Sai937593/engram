"""Task validation helpers and constants."""

from __future__ import annotations

from engram.db import get_db_connection as _get_db_connection
from engram.services.errors import EngramServiceError as _EngramServiceError
from engram.services.errors import ValidationError as _ValidationError

VALID_TASK_STATUSES = {
    "open",
    "in_progress",
    "blocked",
    "done",
    "cancelled",
    "all",
}
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
    "memory_review_outcome",
}


def _normalize_phase_title(title: str | None) -> str:
    """Return a case-insensitive, whitespace-normalized phase key."""
    if title is None:
        return ""
    return " ".join(title.split()).casefold()


def resolve_task_ref(project_id: str, task_ref: str) -> str:
    """Resolve a project-scoped task reference to a single task ID."""
    normalized_ref = task_ref.strip()

    conn = _get_db_connection()
    rows = conn.execute(
        "SELECT id FROM tasks WHERE project_id = ? AND (id = ? OR id LIKE ?)",
        (project_id, normalized_ref, normalized_ref + "%"),
    ).fetchall()
    conn.close()

    matching_ids = sorted({str(row["id"]) for row in rows})

    if not matching_ids:
        raise _EngramServiceError(
            code="TASK_NOT_FOUND",
            message="Task reference was not found in this project.",
            details={"project_id": project_id, "task_ref": normalized_ref},
        )

    if len(matching_ids) > 1:
        if normalized_ref in matching_ids:
            return normalized_ref
        raise _EngramServiceError(
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

    conn = _get_db_connection()
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
        raise _ValidationError(
            code="DEPENDENCY_CYCLE",
            message="Circular dependency detected.",
            details={"task_id": task_id, "depends_on": depends_on_id},
        )


def validate_status_field(status: str) -> None:
    """Validate that a task status is valid (excluding 'all')."""
    allowed = VALID_TASK_STATUSES - {"all"}
    if status not in allowed:
        raise _ValidationError(
            code="INVALID_TASK_STATUS",
            message="Task status is invalid.",
            details={"status": status, "allowed_statuses": sorted(allowed)},
        )


def validate_priority_field(priority: str) -> None:
    """Validate that a task priority is valid."""
    allowed = {"critical", "high", "medium", "low"}
    if priority not in allowed:
        raise _ValidationError(
            code="INVALID_TASK_PRIORITY",
            message="Task priority is invalid.",
            details={"priority": priority, "allowed_priorities": sorted(allowed)},
        )


def validate_memory_review_outcome_field(outcome: str | None) -> None:
    """Validate that a task memory review outcome is valid."""
    if outcome is None:
        return
    allowed = {"created", "superseded", "demoted", "archived", "deleted", "no_change"}
    if outcome not in allowed:
        raise _ValidationError(
            code="INVALID_MEMORY_REVIEW_OUTCOME",
            message="Task memory review outcome is invalid.",
            details={"outcome": outcome, "allowed_outcomes": sorted(allowed)},
        )


def validate_ready_promotion_metadata(
    *,
    status: str | None,
    description: str | None,
    acceptance: str | None,
    relevant_files: list[str] | None,
) -> None:
    """Validate metadata quality required to promote a task into ready."""
    return
