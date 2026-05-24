import sqlite3
import warnings
from pathlib import Path

from engram.db_helpers.connection import create_db_connection
from engram.db_helpers.migrations import (
    apply_memories_column_migrations,
    apply_task_status_migrations,
    apply_tasks_column_migrations,
    backfill_legacy_phase_ids,
)
from engram.db_helpers.schema import (
    create_audit_log_table,
    create_memories_fts_and_triggers,
    create_memories_table,
    create_phases_table,
    create_projects_table,
    create_tasks_table,
)

DEFAULT_DB_PATH = Path.home() / ".engram" / "memory.db"


def get_db_connection(db_path=None):
    """Return a sqlite connection configured for Engram."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    return create_db_connection(db_path)


def init_db(db_path=None):
    """Initialize schema and run idempotent migrations."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    create_projects_table(cursor)
    create_tasks_table(cursor)
    create_phases_table(cursor)
    apply_tasks_column_migrations(cursor)
    create_memories_table(cursor)
    apply_memories_column_migrations(cursor)
    create_audit_log_table(cursor)

    try:
        create_memories_fts_and_triggers(cursor)
    except sqlite3.OperationalError as exc:
        warnings.warn(
            f"[engram] FTS5 search is unavailable: {exc}. Memory search will not work.",
            RuntimeWarning,
            stacklevel=2,
        )

    apply_task_status_migrations(cursor)
    backfill_legacy_phase_ids(cursor)

    conn.commit()
    conn.close()
