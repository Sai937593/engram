import sqlite3
import warnings
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".engram" / "memory.db"


def get_db_connection(db_path=None):
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def init_db(db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Projects
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        summary     TEXT,
        status      TEXT DEFAULT 'active',
        repo_paths  TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        updated_at  TEXT DEFAULT (datetime('now'))
    )
    """)

    # Tasks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id          TEXT PRIMARY KEY,
        project_id  TEXT NOT NULL REFERENCES projects(id),
        phase_id    TEXT REFERENCES phases(id),
        title       TEXT NOT NULL,
        description TEXT,
        status      TEXT DEFAULT 'todo',
        priority    TEXT DEFAULT 'medium',
        phase       TEXT,
        depends_on  TEXT REFERENCES tasks(id),
        acceptance  TEXT,
        evidence    TEXT,
        tags        TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        updated_at  TEXT DEFAULT (datetime('now'))
    )
    """)

    # Phases
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS phases (
        id          TEXT PRIMARY KEY,
        project_id  TEXT NOT NULL REFERENCES projects(id),
        title       TEXT NOT NULL,
        description TEXT,
        status      TEXT DEFAULT 'planned',
        order_index INTEGER DEFAULT 0,
        acceptance  TEXT,
        evidence    TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        updated_at  TEXT DEFAULT (datetime('now'))
    )
    """)

    # Migrations: add missing columns to existing tasks DBs
    if not _column_exists(cursor, "tasks", "depends_on"):
        cursor.execute("ALTER TABLE tasks ADD COLUMN depends_on TEXT REFERENCES tasks(id)")
    if not _column_exists(cursor, "tasks", "phase_id"):
        cursor.execute("ALTER TABLE tasks ADD COLUMN phase_id TEXT REFERENCES phases(id)")

    # Memories
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id             TEXT PRIMARY KEY,
        project_id     TEXT NOT NULL REFERENCES projects(id),
        type           TEXT NOT NULL,
        title          TEXT NOT NULL,
        content        TEXT NOT NULL,
        scope          TEXT DEFAULT 'project',
        task_id        TEXT REFERENCES tasks(id),
        tags           TEXT,
        always_include BOOLEAN DEFAULT 0,
        created_at     TEXT DEFAULT (datetime('now')),
        updated_at     TEXT DEFAULT (datetime('now'))
    )
    """)

    # Sessions table removed for 2-Command Workflow migration

    # Audit Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        target_table TEXT NOT NULL,
        target_id    TEXT NOT NULL,
        operation    TEXT NOT NULL,
        field        TEXT,
        old_value    TEXT,
        new_value    TEXT,
        timestamp    TEXT DEFAULT (datetime('now'))
    )
    """)

    # FTS5 Index for memories
    try:
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            title, content, tags,
            content='memories',
            content_rowid='rowid'
        )
        """)

        # Triggers to keep FTS5 in sync
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
          INSERT INTO memories_fts(rowid, title, content, tags) VALUES (new.rowid, new.title, new.content, new.tags);
        END;
        """)
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
          INSERT INTO memories_fts(memories_fts, rowid, title, content, tags) VALUES('delete', old.rowid, old.title, old.content, old.tags);
        END;
        """)
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
          INSERT INTO memories_fts(memories_fts, rowid, title, content, tags) VALUES('delete', old.rowid, old.title, old.content, old.tags);
          INSERT INTO memories_fts(rowid, title, content, tags) VALUES (new.rowid, new.title, new.content, new.tags);
        END;
        """)
    except sqlite3.OperationalError as e:
        warnings.warn(
            f"[engram] FTS5 search is unavailable: {e}. Memory search will not work.",
            RuntimeWarning,
            stacklevel=2,
        )

    # Migration: rename 'backlog' status to 'todo' (one-time, idempotent)
    cursor.execute("UPDATE tasks SET status = 'todo' WHERE status = 'backlog'")

    # Migration: normalise 'completed' → 'done' (legacy status, not in current enum)
    cursor.execute("UPDATE tasks SET status = 'done' WHERE status = 'completed'")

    conn.commit()
    conn.close()
