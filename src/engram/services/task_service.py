"""Task service read operations."""

from __future__ import annotations

from engram.db import get_db_connection
from engram.services.errors import EngramServiceError


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
