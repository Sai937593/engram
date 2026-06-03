"""Workflow verification migration helpers."""

import sqlite3

from .migrations import column_exists


def apply_workflow_verification_migrations(cursor: sqlite3.Cursor) -> None:
    """Ensure workflow verification table columns exist for legacy upgrades."""
    if not column_exists(cursor, "workflow_verifications", "details"):
        cursor.execute("ALTER TABLE workflow_verifications ADD COLUMN details TEXT")
    if not column_exists(cursor, "workflow_verifications", "verified_at"):
        cursor.execute("ALTER TABLE workflow_verifications ADD COLUMN verified_at TEXT")
