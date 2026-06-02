import sqlite3
import warnings
from pathlib import Path

from .connection import create_db_connection
from .migrations import (
    apply_identity_key_migrations,
    apply_memories_column_migrations,
    apply_task_status_migrations,
    apply_tasks_column_migrations,
    apply_workflow_verification_migrations,
    backfill_legacy_phase_ids,
)
from .schema import (
    create_audit_log_table,
    create_indexes,
    create_memories_fts_and_triggers,
    create_memories_table,
    create_phases_table,
    create_projects_table,
    create_tasks_table,
    create_workflow_verifications_table,
)
from .task_dependency_migrations import apply_task_dependency_ref_migrations


def get_default_db_path() -> Path:
    """Resolve the dynamic default database path."""
    try:
        from engram.services.project_path import get_repo_local_db_path

        return get_repo_local_db_path()
    except Exception:
        return Path.home() / ".engram" / "memory.db"


def __getattr__(name: str):
    if name == "DEFAULT_DB_PATH":
        return get_default_db_path()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_db_connection(db_path=None):
    """Return a sqlite connection configured for Engram."""
    if db_path is None:
        db_path = globals().get("DEFAULT_DB_PATH", get_default_db_path())
    return create_db_connection(db_path)


def init_db(db_path=None):
    """Initialize schema and run idempotent migrations."""
    if db_path is None:
        db_path = globals().get("DEFAULT_DB_PATH", get_default_db_path())
    else:
        db_path = Path(db_path)

    # Ensure parent state directories exist
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Drop existing triggers first so column migrations do not fire them and cause issues
    cursor.execute("DROP TRIGGER IF EXISTS memories_ai")
    cursor.execute("DROP TRIGGER IF EXISTS memories_ad")
    cursor.execute("DROP TRIGGER IF EXISTS memories_au")

    create_projects_table(cursor)
    create_tasks_table(cursor)
    create_phases_table(cursor)
    apply_tasks_column_migrations(cursor)
    create_memories_table(cursor)
    apply_memories_column_migrations(cursor)
    create_workflow_verifications_table(cursor)
    apply_workflow_verification_migrations(cursor)
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
    apply_identity_key_migrations(cursor)
    apply_task_dependency_ref_migrations(cursor)
    create_indexes(cursor)

    conn.commit()
    conn.close()
