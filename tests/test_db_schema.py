"""Tests for the database schema creation functions."""

import sqlite3

import pytest

from engram.db.schema import (
    create_audit_log_table,
    create_indexes,
    create_memories_fts_and_triggers,
    create_memories_table,
    create_phases_table,
    create_projects_table,
    create_tasks_table,
)


@pytest.fixture
def cursor():
    """Provide a fresh SQLite cursor for a memory database."""
    conn = sqlite3.connect(":memory:")
    yield conn.cursor()
    conn.close()


def get_table_columns(cursor: sqlite3.Cursor, table_name: str) -> list[str]:
    """Helper to get column names for a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def get_indexes(cursor: sqlite3.Cursor) -> list[str]:
    """Helper to get index names."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    return [row[0] for row in cursor.fetchall()]


def get_triggers(cursor: sqlite3.Cursor) -> list[str]:
    """Helper to get trigger names."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    return [row[0] for row in cursor.fetchall()]


def get_tables(cursor: sqlite3.Cursor) -> list[str]:
    """Helper to get table names."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cursor.fetchall()]


def test_create_projects_table(cursor):
    """Test creating the projects table."""
    create_projects_table(cursor)

    columns = get_table_columns(cursor, "projects")
    expected_columns = ["id", "name", "summary", "status", "repo_paths", "created_at", "updated_at"]
    assert columns == expected_columns

    # Verify IF NOT EXISTS works by calling again
    create_projects_table(cursor)


def test_create_tasks_table(cursor):
    """Test creating the tasks table."""
    create_tasks_table(cursor)

    columns = get_table_columns(cursor, "tasks")
    expected_columns = [
        "id",
        "project_id",
        "phase_id",
        "title",
        "description",
        "status",
        "priority",
        "phase",
        "depends_on",
        "acceptance",
        "evidence",
        "tags",
        "relevant_files",
        "created_at",
        "updated_at",
    ]
    assert columns == expected_columns

    create_tasks_table(cursor)


def test_create_phases_table(cursor):
    """Test creating the phases table."""
    create_phases_table(cursor)

    columns = get_table_columns(cursor, "phases")
    expected_columns = [
        "id",
        "project_id",
        "title",
        "description",
        "status",
        "order_index",
        "acceptance",
        "evidence",
        "created_at",
        "updated_at",
    ]
    assert columns == expected_columns

    create_phases_table(cursor)


def test_create_memories_table(cursor):
    """Test creating the memories table."""
    create_memories_table(cursor)

    columns = get_table_columns(cursor, "memories")
    expected_columns = [
        "id",
        "project_id",
        "type",
        "title",
        "content",
        "scope",
        "level",
        "task_id",
        "tags",
        "always_include",
        "superseded_by",
        "created_at",
        "updated_at",
    ]
    assert columns == expected_columns

    create_memories_table(cursor)


def test_create_audit_log_table(cursor):
    """Test creating the audit_log table."""
    create_audit_log_table(cursor)

    columns = get_table_columns(cursor, "audit_log")
    expected_columns = [
        "id",
        "target_table",
        "target_id",
        "operation",
        "field",
        "old_value",
        "new_value",
        "timestamp",
    ]
    assert columns == expected_columns

    create_audit_log_table(cursor)


def test_create_memories_fts_and_triggers(cursor):
    """Test creating FTS table and triggers."""
    create_memories_table(cursor)
    create_memories_fts_and_triggers(cursor)

    tables = get_tables(cursor)
    assert "memories_fts" in tables

    triggers = get_triggers(cursor)
    expected_triggers = ["memories_ai", "memories_ad", "memories_au"]
    for trigger in expected_triggers:
        assert trigger in triggers

    create_memories_fts_and_triggers(cursor)


def test_create_indexes(cursor):
    """Test creating secondary indexes."""
    create_projects_table(cursor)
    create_tasks_table(cursor)
    create_phases_table(cursor)
    create_memories_table(cursor)

    create_indexes(cursor)

    indexes = get_indexes(cursor)
    assert "idx_memories_project_id" in indexes
    assert "idx_tasks_project_id" in indexes
    assert "idx_phases_project_id" in indexes

    create_indexes(cursor)
