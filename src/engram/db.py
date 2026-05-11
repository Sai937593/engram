import sqlite3
import os
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".engram" / "memory.db"

def get_db_connection(db_path=None):
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

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
        title       TEXT NOT NULL,
        description TEXT,
        status      TEXT DEFAULT 'backlog',
        priority    TEXT DEFAULT 'medium',
        phase       TEXT,
        acceptance  TEXT,
        evidence    TEXT,
        tags        TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        updated_at  TEXT DEFAULT (datetime('now'))
    )
    """)

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

    # Sessions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id            TEXT PRIMARY KEY,
        project_id    TEXT NOT NULL REFERENCES projects(id),
        goal          TEXT,
        status        TEXT DEFAULT 'open',
        summary       TEXT,
        changed_files TEXT,
        checks_run    TEXT,
        next_steps    TEXT,
        next_task_id  TEXT,
        started_at    TEXT DEFAULT (datetime('now')),
        closed_at     TEXT
    )
    """)

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
    except sqlite3.OperationalError:
        # Fallback if FTS5 is not available (though it usually is in modern Python)
        pass

    conn.commit()
    conn.close()
