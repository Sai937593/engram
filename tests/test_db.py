import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from engram.db import DEFAULT_DB_PATH, get_db_connection, init_db


def test_get_db_connection_default_path(monkeypatch):
    """Test get_db_connection uses DEFAULT_DB_PATH when no path is provided."""
    mock_create = MagicMock()
    monkeypatch.setattr("engram.db.create_db_connection", mock_create)

    get_db_connection()
    mock_create.assert_called_once_with(DEFAULT_DB_PATH)


def test_get_default_db_path_resolves_repo_local(tmp_path, monkeypatch):
    """Test that get_default_db_path resolves to repo-local path in git repo."""
    repo_path = tmp_path / "my_git_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    monkeypatch.setattr("os.getcwd", lambda: str(repo_path))

    from engram.db import get_default_db_path

    path = get_default_db_path()
    assert path == repo_path / ".engram" / "memory.db"


def test_get_default_db_path_fallback_outside_repo(tmp_path, monkeypatch):
    """Test that get_default_db_path falls back to home directory if outside a repo."""
    outside_path = tmp_path / "not_a_repo"
    outside_path.mkdir()

    monkeypatch.setattr("os.getcwd", lambda: str(outside_path))

    from engram.db import get_default_db_path

    path = get_default_db_path()
    assert path == Path.home() / ".engram" / "memory.db"


def test_init_db_creates_parent_directory(tmp_path, monkeypatch):
    """Test that init_db automatically creates the parent directory of the DB path."""
    db_path = tmp_path / "new_subdir" / "test_memory.db"
    assert not db_path.parent.exists()

    # Mock all internal init_db steps to avoid schema creation errors during simple dir test
    monkeypatch.setattr("engram.db.get_db_connection", MagicMock())
    monkeypatch.setattr("engram.db.create_projects_table", MagicMock())
    monkeypatch.setattr("engram.db.create_tasks_table", MagicMock())
    monkeypatch.setattr("engram.db.create_phases_table", MagicMock())
    monkeypatch.setattr("engram.db.apply_tasks_column_migrations", MagicMock())
    monkeypatch.setattr("engram.db.create_memories_table", MagicMock())
    monkeypatch.setattr("engram.db.apply_memories_column_migrations", MagicMock())
    monkeypatch.setattr("engram.db.create_audit_log_table", MagicMock())
    monkeypatch.setattr("engram.db.create_indexes", MagicMock())
    monkeypatch.setattr("engram.db.create_memories_fts_and_triggers", MagicMock())
    monkeypatch.setattr("engram.db.apply_task_status_migrations", MagicMock())
    monkeypatch.setattr("engram.db.backfill_legacy_phase_ids", MagicMock())
    monkeypatch.setattr("engram.db.apply_task_dependency_ref_migrations", MagicMock())

    init_db(db_path)
    assert db_path.parent.exists()


def test_monkeypatch_override_works(monkeypatch):
    """Test that standard monkeypatch overrides of DEFAULT_DB_PATH are successful."""
    custom_path = Path("/mock/test/db.sqlite")
    monkeypatch.setattr("engram.db.DEFAULT_DB_PATH", custom_path)

    from engram.db import DEFAULT_DB_PATH

    assert DEFAULT_DB_PATH == custom_path


def test_get_db_connection_custom_path(monkeypatch):
    """Test get_db_connection passes the provided custom path."""
    mock_create = MagicMock()
    monkeypatch.setattr("engram.db.create_db_connection", mock_create)

    custom_path = Path("/custom/path/db.sqlite")
    get_db_connection(custom_path)
    mock_create.assert_called_once_with(custom_path)


def test_init_db_calls_all_schema_functions(monkeypatch):
    """Test init_db creates a cursor and calls all schema/migration functions."""
    # Mock connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock get_db_connection
    mock_get_db_connection = MagicMock(return_value=mock_conn)
    monkeypatch.setattr("engram.db.get_db_connection", mock_get_db_connection)

    # Mock all schema and migration functions
    mock_create_projects_table = MagicMock()
    mock_create_tasks_table = MagicMock()
    mock_create_phases_table = MagicMock()
    mock_apply_tasks_column_migrations = MagicMock()
    mock_create_memories_table = MagicMock()
    mock_apply_memories_column_migrations = MagicMock()
    mock_create_audit_log_table = MagicMock()
    mock_create_indexes = MagicMock()
    mock_create_memories_fts_and_triggers = MagicMock()
    mock_apply_task_status_migrations = MagicMock()
    mock_backfill_legacy_phase_ids = MagicMock()
    mock_apply_task_dependency_ref_migrations = MagicMock()

    monkeypatch.setattr("engram.db.create_projects_table", mock_create_projects_table)
    monkeypatch.setattr("engram.db.create_tasks_table", mock_create_tasks_table)
    monkeypatch.setattr("engram.db.create_phases_table", mock_create_phases_table)
    monkeypatch.setattr(
        "engram.db.apply_tasks_column_migrations", mock_apply_tasks_column_migrations
    )
    monkeypatch.setattr("engram.db.create_memories_table", mock_create_memories_table)
    monkeypatch.setattr(
        "engram.db.apply_memories_column_migrations", mock_apply_memories_column_migrations
    )
    monkeypatch.setattr("engram.db.create_audit_log_table", mock_create_audit_log_table)
    monkeypatch.setattr("engram.db.create_indexes", mock_create_indexes)
    monkeypatch.setattr(
        "engram.db.create_memories_fts_and_triggers", mock_create_memories_fts_and_triggers
    )
    monkeypatch.setattr("engram.db.apply_task_status_migrations", mock_apply_task_status_migrations)
    monkeypatch.setattr("engram.db.backfill_legacy_phase_ids", mock_backfill_legacy_phase_ids)
    monkeypatch.setattr(
        "engram.db.apply_task_dependency_ref_migrations", mock_apply_task_dependency_ref_migrations
    )

    # Call init_db
    custom_path = Path("/custom/path/db.sqlite")
    init_db(custom_path)

    # Assertions
    mock_get_db_connection.assert_called_once_with(custom_path)
    mock_conn.cursor.assert_called_once()

    mock_create_projects_table.assert_called_once_with(mock_cursor)
    mock_create_tasks_table.assert_called_once_with(mock_cursor)
    mock_create_phases_table.assert_called_once_with(mock_cursor)
    mock_apply_tasks_column_migrations.assert_called_once_with(mock_cursor)
    mock_create_memories_table.assert_called_once_with(mock_cursor)
    mock_apply_memories_column_migrations.assert_called_once_with(mock_cursor)
    mock_create_audit_log_table.assert_called_once_with(mock_cursor)
    mock_create_indexes.assert_called_once_with(mock_cursor)
    mock_create_memories_fts_and_triggers.assert_called_once_with(mock_cursor)
    mock_apply_task_status_migrations.assert_called_once_with(mock_cursor)
    mock_backfill_legacy_phase_ids.assert_called_once_with(mock_cursor)
    mock_apply_task_dependency_ref_migrations.assert_called_once_with(mock_cursor)

    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()


def test_init_db_handles_fts5_error(monkeypatch):
    """Test init_db handles sqlite3.OperationalError for FTS5 gracefully."""
    # Mock connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock get_db_connection
    mock_get_db_connection = MagicMock(return_value=mock_conn)
    monkeypatch.setattr("engram.db.get_db_connection", mock_get_db_connection)

    # Mock all schema and migration functions to do nothing, except FTS
    monkeypatch.setattr("engram.db.create_projects_table", MagicMock())
    monkeypatch.setattr("engram.db.create_tasks_table", MagicMock())
    monkeypatch.setattr("engram.db.create_phases_table", MagicMock())
    monkeypatch.setattr("engram.db.apply_tasks_column_migrations", MagicMock())
    monkeypatch.setattr("engram.db.create_memories_table", MagicMock())
    monkeypatch.setattr("engram.db.apply_memories_column_migrations", MagicMock())
    monkeypatch.setattr("engram.db.create_audit_log_table", MagicMock())
    monkeypatch.setattr("engram.db.create_indexes", MagicMock())

    # This one will raise
    def mock_raise_fts(*args, **kwargs):
        raise sqlite3.OperationalError("no such module: fts5")

    monkeypatch.setattr("engram.db.create_memories_fts_and_triggers", mock_raise_fts)

    mock_apply_task_status_migrations = MagicMock()
    mock_backfill_legacy_phase_ids = MagicMock()
    mock_apply_task_dependency_ref_migrations = MagicMock()
    monkeypatch.setattr("engram.db.apply_task_status_migrations", mock_apply_task_status_migrations)
    monkeypatch.setattr("engram.db.backfill_legacy_phase_ids", mock_backfill_legacy_phase_ids)
    monkeypatch.setattr(
        "engram.db.apply_task_dependency_ref_migrations", mock_apply_task_dependency_ref_migrations
    )

    with pytest.warns(RuntimeWarning, match="FTS5 search is unavailable"):
        init_db()

    # The functions after the exception should still have been called
    mock_apply_task_status_migrations.assert_called_once_with(mock_cursor)
    mock_backfill_legacy_phase_ids.assert_called_once_with(mock_cursor)
    mock_apply_task_dependency_ref_migrations.assert_called_once_with(mock_cursor)


def test_init_db_normalizes_legacy_dependency_refs(tmp_db):
    """Legacy textual dependency refs are normalized to task IDs during init_db."""
    conn = get_db_connection(tmp_db)
    conn.execute(
        "INSERT INTO projects (id, name, summary, status, repo_paths) VALUES (?, ?, ?, ?, ?)",
        ("proj-dep", "Dep Project", "summary", "active", "[]"),
    )
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, status, priority) VALUES (?, ?, ?, ?, ?)",
        ("a1b2c3d4", "proj-dep", "2.3 Example prerequisite", "done", "high"),
    )
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, status, priority, depends_on) VALUES (?, ?, ?, ?, ?, ?)",
        (
            "d4c3b2a1",
            "proj-dep",
            "2.4 Task with legacy dependency",
            "todo",
            "high",
            "2.3",
        ),
    )
    conn.commit()
    conn.close()

    init_db(tmp_db)

    conn = get_db_connection(tmp_db)
    dep_value = conn.execute(
        "SELECT depends_on FROM tasks WHERE id = ?",
        ("d4c3b2a1",),
    ).fetchone()["depends_on"]
    conn.close()
    assert dep_value == "a1b2c3d4"
