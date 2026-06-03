"""Identity key migration helpers."""

import sqlite3

from .migrations import column_exists


def apply_identity_key_migrations(cursor: sqlite3.Cursor) -> None:
    """Ensure project, phase, and task key columns exist and are backfilled."""
    if not column_exists(cursor, "projects", "plan_key"):
        cursor.execute("ALTER TABLE projects ADD COLUMN plan_key TEXT")
    if not column_exists(cursor, "phases", "key"):
        cursor.execute("ALTER TABLE phases ADD COLUMN key TEXT")
    if not column_exists(cursor, "tasks", "key"):
        cursor.execute("ALTER TABLE tasks ADD COLUMN key TEXT")

    cursor.execute(
        """
        UPDATE projects
        SET plan_key = id
        WHERE plan_key IS NULL OR TRIM(plan_key) = ''
        """
    )
    cursor.execute(
        """
        UPDATE phases
        SET key = id
        WHERE key IS NULL OR TRIM(key) = ''
        """
    )
    cursor.execute(
        """
        UPDATE tasks
        SET key = id
        WHERE key IS NULL OR TRIM(key) = ''
        """
    )
