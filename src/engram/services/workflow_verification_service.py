"""Persistence and lookup helpers for workflow verification results."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
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


def _parse_verified_at(verified_at: str | None) -> datetime | None:
    """Parse a persisted verification timestamp into a datetime object."""
    if not verified_at:
        return None
    try:
        return datetime.fromisoformat(verified_at)
    except ValueError:
        return None


def _latest_relevant_file_mtime(repo_path: str, relevant_files: list[str]) -> datetime | None:
    """Return the latest mtime across existing relevant files under the repo path."""
    latest: datetime | None = None
    for rel in relevant_files:
        candidate = (Path(repo_path) / rel).resolve()
        if not candidate.exists() or not candidate.is_file():
            continue
        modified_at = datetime.fromtimestamp(candidate.stat().st_mtime)
        if latest is None or modified_at > latest:
            latest = modified_at
    return latest


def evaluate_verification_eligibility(
    project_id: str, task_id: str, repo_path: str, relevant_files: list[str] | None = None
) -> dict[str, Any]:
    """Classify finish eligibility from the latest verification record and change evidence."""
    record = get_latest_workflow_verification(project_id=project_id, task_id=task_id)
    if not record:
        return {
            "allowed": False,
            "state": "missing",
            "reason_code": "VERIFICATION_MISSING",
            "reason": "No verification record exists for the active task.",
            "record": None,
        }

    status = str(record.get("status") or "").strip().lower()
    if status == "failed":
        return {
            "allowed": False,
            "state": "failed",
            "reason_code": "VERIFICATION_FAILED",
            "reason": "The latest verification for the active task failed.",
            "record": record,
        }
    if status != "passed":
        return {
            "allowed": False,
            "state": "failed",
            "reason_code": "VERIFICATION_INVALID_STATUS",
            "reason": f"Latest verification has unsupported status '{status or 'unknown'}'.",
            "record": record,
        }

    verified_at = _parse_verified_at(record.get("verified_at"))
    if verified_at and relevant_files:
        latest_mtime = _latest_relevant_file_mtime(repo_path, relevant_files)
        if latest_mtime and latest_mtime > verified_at:
            return {
                "allowed": False,
                "state": "stale",
                "reason_code": "VERIFICATION_STALE_RELEVANT_CHANGES",
                "reason": "Relevant files changed after the latest successful verification.",
                "record": record,
            }

    return {
        "allowed": True,
        "state": "passed",
        "reason_code": "VERIFICATION_PASSED",
        "reason": "Latest verification passed and is eligible for finish.",
        "record": record,
    }
