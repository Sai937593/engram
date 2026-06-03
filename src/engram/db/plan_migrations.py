"""Plan migration helpers."""

import sqlite3

from .migrations import column_exists


def apply_plans_column_migrations(cursor: sqlite3.Cursor) -> None:
    """Add missing legacy plans columns for compatibility."""
    if not column_exists(cursor, "plans", "project_id"):
        cursor.execute("ALTER TABLE plans ADD COLUMN project_id TEXT")
    if not column_exists(cursor, "plans", "key"):
        cursor.execute("ALTER TABLE plans ADD COLUMN key TEXT")
    if not column_exists(cursor, "plans", "title"):
        cursor.execute("ALTER TABLE plans ADD COLUMN title TEXT")
    if not column_exists(cursor, "plans", "slug"):
        cursor.execute("ALTER TABLE plans ADD COLUMN slug TEXT")
    if not column_exists(cursor, "plans", "status"):
        cursor.execute("ALTER TABLE plans ADD COLUMN status TEXT")
    if not column_exists(cursor, "plans", "source_doc_path"):
        cursor.execute("ALTER TABLE plans ADD COLUMN source_doc_path TEXT")
    if not column_exists(cursor, "plans", "created_at"):
        cursor.execute("ALTER TABLE plans ADD COLUMN created_at TEXT")
    if not column_exists(cursor, "plans", "updated_at"):
        cursor.execute("ALTER TABLE plans ADD COLUMN updated_at TEXT")
