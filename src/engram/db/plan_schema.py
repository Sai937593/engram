"""Plan schema helpers."""

import sqlite3


def create_plans_table(cursor: sqlite3.Cursor) -> None:
    """Create the plans table when missing."""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plans (
        id              TEXT PRIMARY KEY,
        project_id      TEXT NOT NULL REFERENCES projects(id),
        key             TEXT,
        title           TEXT NOT NULL,
        slug            TEXT,
        status          TEXT DEFAULT 'draft',
        source_doc_path TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now')),
        CHECK (status IN ('draft', 'active', 'review_pending', 'done', 'archived', 'cancelled'))
    )
    """)
