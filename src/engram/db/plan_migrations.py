"""Plan migration helpers."""

from __future__ import annotations

import re
import sqlite3
import uuid

from .migrations import column_exists

_CANONICAL_PLAN_KEY_RE = re.compile(r"^p\d{4}$", re.IGNORECASE)


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


def _is_canonical_plan_key(value: str | None) -> bool:
    """Return whether a legacy plan key uses the canonical pNNNN format."""
    if value is None:
        return False
    return bool(_CANONICAL_PLAN_KEY_RE.fullmatch(value.strip()))


def backfill_legacy_project_plans(cursor: sqlite3.Cursor) -> None:
    """Backfill first-class plan rows for legacy projects with explicit plan keys."""
    if not column_exists(cursor, "projects", "plan_key"):
        return

    project_rows = cursor.execute(
        """
        SELECT id, name, plan_key, active_plan_id
        FROM projects
        """
    ).fetchall()
    if not project_rows:
        return

    for row in project_rows:
        raw_plan_key = row["plan_key"]
        if not _is_canonical_plan_key(raw_plan_key):
            continue

        plan_key = raw_plan_key.strip()
        existing_plan = cursor.execute(
            """
            SELECT id
            FROM plans
            WHERE project_id = ? AND key = ?
            """,
            (row["id"], plan_key),
        ).fetchone()

        if existing_plan is None:
            plan_id = uuid.uuid4().hex[:8]
            cursor.execute(
                """
                INSERT INTO plans (id, project_id, key, title, status)
                VALUES (?, ?, ?, ?, 'active')
                """,
                (plan_id, row["id"], plan_key, row["name"]),
            )
        else:
            plan_id = existing_plan["id"]

        if row["active_plan_id"] is None:
            cursor.execute(
                """
                UPDATE projects
                SET active_plan_id = ?
                WHERE id = ? AND active_plan_id IS NULL
                """,
                (plan_id, row["id"]),
            )
