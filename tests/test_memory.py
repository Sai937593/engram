"""Tests for Memory model including FTS5 search."""

import sqlite3

from engram.db import get_db_connection, init_db
from engram.models.memory import Memory


def test_create_memory(project):
    m = Memory.create(
        project_id=project.id,
        type="decision",
        title="Use SQLite",
        content="SQLite is ideal for local-first apps.",
        tags=["storage", "arch"],
    )
    assert m.title == "Use SQLite"
    assert m.type == "decision"
    assert "storage" in m.tags
    assert m.always_include is False


def test_create_memory_always_include(project):
    m = Memory.create(
        project_id=project.id,
        type="constraint",
        title="No production writes",
        content="Never write to production DB directly.",
        always_include=True,
    )
    assert m.always_include is True


def test_get_memory(memory):
    fetched = Memory.get(memory.id)
    assert fetched is not None
    assert fetched.title == memory.title


def test_get_nonexistent_memory(tmp_db):
    assert Memory.get("no-such-id") is None


def test_list_by_project(project):
    Memory.create(project_id=project.id, type="note", title="Note A", content="...")
    Memory.create(project_id=project.id, type="lesson", title="Lesson B", content="...")
    memories = Memory.list_by_project(project.id)
    titles = [m.title for m in memories]
    assert "Note A" in titles
    assert "Lesson B" in titles


def test_list_always_include(project):
    Memory.create(
        project_id=project.id, type="constraint", title="Always", content="x", always_include=True
    )
    Memory.create(
        project_id=project.id, type="note", title="Not always", content="y", always_include=False
    )
    results = Memory.list_always_include(project.id)
    assert len(results) == 1
    assert results[0].title == "Always"


def test_update_memory_content(memory):
    memory.update(content="Updated content here.")
    refreshed = Memory.get(memory.id)
    assert refreshed.content == "Updated content here."


def test_update_memory_tags(memory):
    memory.update(tags=["new-tag", "another"])
    refreshed = Memory.get(memory.id)
    assert "new-tag" in refreshed.tags


def test_update_memory_always_include(memory):
    memory.update(always_include=True)
    refreshed = Memory.get(memory.id)
    assert refreshed.always_include is True


def test_delete_memory(memory):
    memory.delete()
    assert Memory.get(memory.id) is None


def test_fts_search(project):
    Memory.create(
        project_id=project.id,
        type="lesson",
        title="WAL mode",
        content="WAL mode needed for concurrent reads in SQLite.",
    )
    Memory.create(
        project_id=project.id,
        type="note",
        title="Unrelated",
        content="Something completely different.",
    )
    results = Memory.search("WAL concurrent")
    titles = [m.title for m in results]
    assert "WAL mode" in titles


def test_init_db_adds_memories_level_column_for_legacy_databases(tmp_path):
    db_path = tmp_path / "legacy_memory.db"
    legacy_conn = sqlite3.connect(db_path)
    legacy_conn.execute("""
    CREATE TABLE projects (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        summary     TEXT,
        status      TEXT DEFAULT 'active',
        repo_paths  TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        updated_at  TEXT DEFAULT (datetime('now'))
    )
    """)
    legacy_conn.execute("""
    CREATE TABLE tasks (
        id          TEXT PRIMARY KEY,
        project_id  TEXT NOT NULL REFERENCES projects(id),
        title       TEXT NOT NULL,
        description TEXT,
        status      TEXT DEFAULT 'todo',
        priority    TEXT DEFAULT 'medium',
        phase       TEXT,
        acceptance  TEXT,
        evidence    TEXT,
        tags        TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        updated_at  TEXT DEFAULT (datetime('now'))
    )
    """)
    legacy_conn.execute("""
    CREATE TABLE memories (
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
    legacy_conn.execute(
        "INSERT INTO projects (id, name, repo_paths) VALUES ('legacy-proj', 'Legacy', '[]')"
    )
    legacy_conn.execute(
        "INSERT INTO tasks (id, project_id, title) VALUES ('legacy-task', 'legacy-proj', 'Legacy Task')"
    )
    legacy_conn.execute(
        """
        INSERT INTO memories (id, project_id, type, title, content, scope, task_id, tags, always_include)
        VALUES ('legacy-memory-1', 'legacy-proj', 'constraint', 'Legacy Constraint', 'Keep tests green', 'project', NULL, 'quality,testing', 1)
        """
    )
    legacy_conn.execute(
        """
        INSERT INTO memories (id, project_id, type, title, content, scope, task_id, tags, always_include)
        VALUES ('legacy-memory-2', 'legacy-proj', 'note', 'Task Note', 'Scoped to a task', 'task', 'legacy-task', 'task', 0)
        """
    )
    legacy_conn.commit()
    legacy_conn.close()

    init_db(db_path)
    init_db(db_path)

    conn = get_db_connection(db_path)
    memory_columns = {row["name"] for row in conn.execute("PRAGMA table_info(memories)").fetchall()}
    memory_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    migrated_row = conn.execute("SELECT * FROM memories WHERE id = 'legacy-memory-2'").fetchone()
    conn.close()

    assert "level" in memory_columns
    assert memory_count == 2
    migrated_memory = Memory.from_row(migrated_row)
    assert migrated_memory.scope == "task"
    assert migrated_memory.task_id == "legacy-task"
    assert migrated_memory.level is None


def test_memory_from_row_preserves_scope_and_level(tmp_db, project):
    conn = get_db_connection(tmp_db)
    conn.execute(
        """
        INSERT INTO memories (
            id, project_id, type, title, content, scope, level, task_id, tags, always_include
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "project-level-memory",
            project.id,
            "decision",
            "Structured Level",
            "Memory with level.",
            "project",
            "L2",
            None,
            "architecture",
            0,
        ),
    )
    conn.execute(
        """
        INSERT INTO memories (
            id, project_id, type, title, content, scope, level, task_id, tags, always_include
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "task-level-memory",
            project.id,
            "note",
            "Task Scoped",
            "Memory without level.",
            "task",
            None,
            "task-123",
            "task",
            0,
        ),
    )
    conn.commit()
    row_project = conn.execute(
        "SELECT * FROM memories WHERE id = 'project-level-memory'"
    ).fetchone()
    row_task = conn.execute("SELECT * FROM memories WHERE id = 'task-level-memory'").fetchone()
    conn.close()

    project_memory = Memory.from_row(row_project)
    task_memory = Memory.from_row(row_task)

    assert project_memory.scope == "project"
    assert project_memory.level == "L2"
    assert task_memory.scope == "task"
    assert task_memory.level is None


def test_init_db_backfills_legacy_memory_scope_and_level_defaults(tmp_path):
    db_path = tmp_path / "legacy_memory_backfill.db"
    legacy_conn = sqlite3.connect(db_path)
    legacy_conn.execute("""
    CREATE TABLE projects (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        summary     TEXT,
        status      TEXT DEFAULT 'active',
        repo_paths  TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        updated_at  TEXT DEFAULT (datetime('now'))
    )
    """)
    legacy_conn.execute("""
    CREATE TABLE tasks (
        id          TEXT PRIMARY KEY,
        project_id  TEXT NOT NULL REFERENCES projects(id),
        title       TEXT NOT NULL,
        description TEXT,
        status      TEXT DEFAULT 'todo',
        priority    TEXT DEFAULT 'medium',
        phase       TEXT,
        acceptance  TEXT,
        evidence    TEXT,
        tags        TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        updated_at  TEXT DEFAULT (datetime('now'))
    )
    """)
    legacy_conn.execute("""
    CREATE TABLE memories (
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
    legacy_conn.execute(
        "INSERT INTO projects (id, name, repo_paths) VALUES ('legacy-proj', 'Legacy', '[]')"
    )
    legacy_conn.execute(
        "INSERT INTO tasks (id, project_id, title) VALUES ('legacy-task', 'legacy-proj', 'Legacy Task')"
    )

    fixture_rows = [
        (
            "legacy-constraint",
            "constraint",
            "Constraint",
            "No production writes",
            "task",
            "legacy-task",
            "guardrail",
            0,
        ),
        (
            "legacy-decision",
            "decision",
            "Decision",
            "Use sqlite",
            "task",
            "legacy-task",
            "architecture",
            0,
        ),
        (
            "legacy-task-lesson",
            "lesson",
            "Task Lesson",
            "Task linked lesson",
            "project",
            "legacy-task",
            "lesson",
            0,
        ),
        (
            "legacy-task-snippet",
            "snippet",
            "Task Snippet",
            "Task linked snippet",
            "project",
            "legacy-task",
            "snippet",
            1,
        ),
        (
            "legacy-project-lesson",
            "lesson",
            "Project Lesson",
            "Project lesson",
            "project",
            None,
            "lesson",
            0,
        ),
        (
            "legacy-project-note-always",
            "note",
            "Pinned Note",
            "Important note",
            "project",
            None,
            "note",
            1,
        ),
        (
            "legacy-custom-always",
            "custom",
            "Custom Pinned",
            "Pinned custom memory",
            "project",
            None,
            "custom",
            1,
        ),
        (
            "legacy-custom-plain",
            "custom",
            "Custom Plain",
            "Plain custom memory",
            "project",
            None,
            "custom",
            0,
        ),
    ]
    legacy_conn.executemany(
        """
        INSERT INTO memories (id, project_id, type, title, content, scope, task_id, tags, always_include)
        VALUES (?, 'legacy-proj', ?, ?, ?, ?, ?, ?, ?)
        """,
        fixture_rows,
    )
    legacy_conn.commit()
    legacy_conn.close()

    init_db(db_path)
    init_db(db_path)

    conn = get_db_connection(db_path)
    rows = conn.execute(
        """
        SELECT id, type, content, scope, level, task_id, tags, always_include
        FROM memories
        WHERE project_id = 'legacy-proj'
        """
    ).fetchall()
    conn.close()

    by_id = {row["id"]: row for row in rows}
    assert set(by_id) == {row[0] for row in fixture_rows}

    assert by_id["legacy-constraint"]["scope"] == "project"
    assert by_id["legacy-constraint"]["level"] == "L1"
    assert by_id["legacy-constraint"]["task_id"] == "legacy-task"

    assert by_id["legacy-decision"]["scope"] == "project"
    assert by_id["legacy-decision"]["level"] == "L2"
    assert by_id["legacy-decision"]["task_id"] == "legacy-task"

    assert by_id["legacy-task-lesson"]["scope"] == "task"
    assert by_id["legacy-task-lesson"]["level"] is None
    assert by_id["legacy-task-lesson"]["task_id"] == "legacy-task"

    assert by_id["legacy-task-snippet"]["scope"] == "task"
    assert by_id["legacy-task-snippet"]["level"] is None
    assert by_id["legacy-task-snippet"]["task_id"] == "legacy-task"

    assert by_id["legacy-project-lesson"]["scope"] == "project"
    assert by_id["legacy-project-lesson"]["level"] == "L3"
    assert by_id["legacy-project-lesson"]["task_id"] is None

    assert by_id["legacy-project-note-always"]["scope"] == "project"
    assert by_id["legacy-project-note-always"]["level"] == "L1"
    assert by_id["legacy-project-note-always"]["task_id"] is None

    assert by_id["legacy-custom-always"]["scope"] == "project"
    assert by_id["legacy-custom-always"]["level"] == "L1"
    assert by_id["legacy-custom-always"]["task_id"] is None

    assert by_id["legacy-custom-plain"]["scope"] == "project"
    assert by_id["legacy-custom-plain"]["level"] == "L3"
    assert by_id["legacy-custom-plain"]["task_id"] is None

    for (
        fixture_id,
        _,
        _,
        fixture_content,
        _,
        _,
        fixture_tags,
        fixture_always_include,
    ) in fixture_rows:
        migrated_row = by_id[fixture_id]
        assert migrated_row["content"] == fixture_content
        assert migrated_row["tags"] == fixture_tags
        assert migrated_row["always_include"] == fixture_always_include
