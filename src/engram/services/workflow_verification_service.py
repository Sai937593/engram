"""Persistence and lookup helpers for workflow verification results."""

from __future__ import annotations

from typing import Any

from engram.db import get_db_connection
from engram.services.errors import EngramServiceError


def record_workflow_verification(
    project_id: str,
    passed: bool,
    summary: str,
    task_id: str | None = None,
    workflow_run_ref: str | None = None,
    details: str | None = None,
    verified_at: str | None = None,
) -> dict[str, Any]:
    """Persist one workflow verification result row."""
    if not task_id and not workflow_run_ref:
        raise EngramServiceError(
            code="VALIDATION_ERROR",
            message="Either task_id or workflow_run_ref is required.",
        )
    conn = get_db_connection()
    cursor = conn.cursor()
    status = "passed" if passed else "failed"
    timestamp_sql = "?" if verified_at else "datetime('now')"
    params = [project_id, task_id, workflow_run_ref, status, summary.strip(), details]
    if verified_at:
        params.append(verified_at)
    cursor.execute(
        f"""
        INSERT INTO workflow_verifications (
            project_id, task_id, workflow_run_ref, status, summary, details, verified_at
        ) VALUES (?, ?, ?, ?, ?, ?, {timestamp_sql})
        """,
        params,
    )
    row_id = cursor.lastrowid
    conn.commit()
    row = cursor.execute(
        "SELECT * FROM workflow_verifications WHERE id = ?",
        (row_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def get_latest_workflow_verification(
    project_id: str,
    task_id: str | None = None,
    workflow_run_ref: str | None = None,
) -> dict[str, Any] | None:
    """Return the most recent verification record for a task or workflow run."""
    if not task_id and not workflow_run_ref:
        raise EngramServiceError(
            code="VALIDATION_ERROR",
            message="Either task_id or workflow_run_ref is required.",
        )
    conn = get_db_connection()
    cursor = conn.cursor()
    if task_id:
        row = cursor.execute(
            """
            SELECT * FROM workflow_verifications
            WHERE project_id = ? AND task_id = ?
            ORDER BY verified_at DESC, id DESC
            LIMIT 1
            """,
            (project_id, task_id),
        ).fetchone()
    else:
        row = cursor.execute(
            """
            SELECT * FROM workflow_verifications
            WHERE project_id = ? AND workflow_run_ref = ?
            ORDER BY verified_at DESC, id DESC
            LIMIT 1
            """,
            (project_id, workflow_run_ref),
        ).fetchone()
    conn.close()
    return dict(row) if row else None
