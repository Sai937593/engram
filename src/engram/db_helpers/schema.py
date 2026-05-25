"""Database schema creation helpers."""

import sqlite3


def create_projects_table(cursor: sqlite3.Cursor) -> None:
    """Create the projects table when missing."""
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


def create_tasks_table(cursor: sqlite3.Cursor) -> None:
    """Create the tasks table when missing."""
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
        relevant_files TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        updated_at  TEXT DEFAULT (datetime('now'))
    )
    """)


def create_phases_table(cursor: sqlite3.Cursor) -> None:
    """Create the phases table when missing."""
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


def create_memories_table(cursor: sqlite3.Cursor) -> None:
    """Create the memories table when missing."""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id             TEXT PRIMARY KEY,
        project_id     TEXT NOT NULL REFERENCES projects(id),
        type           TEXT NOT NULL,
        title          TEXT NOT NULL,
        content        TEXT NOT NULL,
        scope          TEXT DEFAULT 'project',
        level          TEXT,
        task_id        TEXT REFERENCES tasks(id),
        tags           TEXT,
        always_include BOOLEAN DEFAULT 0,
        created_at     TEXT DEFAULT (datetime('now')),
        updated_at     TEXT DEFAULT (datetime('now'))
    )
    """)


def create_audit_log_table(cursor: sqlite3.Cursor) -> None:
    """Create the audit_log table when missing."""
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


def create_memories_fts_and_triggers(cursor: sqlite3.Cursor) -> None:
    """Create memories FTS table and sync triggers when FTS5 is available."""
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
        title, content, tags,
        content='memories',
        content_rowid='rowid'
    )
    """)

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
