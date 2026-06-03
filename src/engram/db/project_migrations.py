"""Project migration helpers."""

from __future__ import annotations

import sqlite3

from .migrations import column_exists


def apply_projects_column_migrations(cursor: sqlite3.Cursor) -> None:
    """Add missing legacy projects columns for compatibility."""
    if not column_exists(cursor, "projects", "active_plan_id"):
        cursor.execute("ALTER TABLE projects ADD COLUMN active_plan_id TEXT REFERENCES plans(id)")
