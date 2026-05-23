"""Unit tests for legacy phase migration edge cases."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from engram.db import init_db


def _create_legacy_schema(db_path: Path) -> None:
    """Create a legacy schema where tasks have `phase` but no `phase_id`."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE projects (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            summary     TEXT,
            status      TEXT DEFAULT 'active',
            repo_paths  TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
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
        """
    )
    conn.commit()
    conn.close()


def test_init_db_migrates_duplicate_legacy_phase_titles_with_mixed_casing(tmp_path: Path) -> None:
    """Migration should merge duplicate legacy phase labels by normalized title."""
    db_path = tmp_path / "legacy_mixed_case.db"
    _create_legacy_schema(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO projects (id, name, repo_paths) VALUES ('proj-1', 'Project 1', '[]')")
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, phase) VALUES ('t1', 'proj-1', 'Task 1', ' Phase Alpha ')"
    )
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, phase) VALUES ('t2', 'proj-1', 'Task 2', 'phase   alpha')"
    )
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, phase) VALUES ('t3', 'proj-1', 'Task 3', 'PHASE alpha')"
    )
    conn.commit()
    conn.close()

    init_db(db_path)

    conn = sqlite3.connect(db_path)
    phase_rows = conn.execute("SELECT id, title FROM phases WHERE project_id = 'proj-1'").fetchall()
    task_phase_ids = dict(conn.execute("SELECT id, phase_id FROM tasks ORDER BY id").fetchall())
    conn.close()

    assert len(phase_rows) == 1
    assert " ".join(phase_rows[0][1].split()).casefold() == "phase alpha"
    assert task_phase_ids["t1"] == task_phase_ids["t2"] == task_phase_ids["t3"]
    assert task_phase_ids["t1"] is not None


def test_init_db_ignores_empty_or_null_legacy_phase_titles(tmp_path: Path) -> None:
    """Migration should not create phases for empty/whitespace/null legacy phase values."""
    db_path = tmp_path / "legacy_empty_null.db"
    _create_legacy_schema(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO projects (id, name, repo_paths) VALUES ('proj-1', 'Project 1', '[]')")
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, phase) VALUES ('t1', 'proj-1', 'Task 1', '')"
    )
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, phase) VALUES ('t2', 'proj-1', 'Task 2', '   ')"
    )
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, phase) VALUES ('t3', 'proj-1', 'Task 3', NULL)"
    )
    conn.commit()
    conn.close()

    init_db(db_path)

    conn = sqlite3.connect(db_path)
    phase_count = conn.execute(
        "SELECT COUNT(*) FROM phases WHERE project_id = 'proj-1'"
    ).fetchone()[0]
    task_phase_ids = dict(conn.execute("SELECT id, phase_id FROM tasks ORDER BY id").fetchall())
    conn.close()

    assert phase_count == 0
    assert task_phase_ids == {"t1": None, "t2": None, "t3": None}


def test_init_db_legacy_phase_backfill_is_idempotent(tmp_path: Path) -> None:
    """Running init_db repeatedly should not create duplicate phases or re-link tasks differently."""
    db_path = tmp_path / "legacy_idempotent.db"
    _create_legacy_schema(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO projects (id, name, repo_paths) VALUES ('proj-1', 'Project 1', '[]')")
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, phase) VALUES ('t1', 'proj-1', 'Task 1', 'Phase Beta')"
    )
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, phase) VALUES ('t2', 'proj-1', 'Task 2', ' phase   beta ')"
    )
    conn.commit()
    conn.close()

    init_db(db_path)

    conn = sqlite3.connect(db_path)
    first_phase_rows = conn.execute(
        "SELECT id, project_id, title, status, order_index FROM phases ORDER BY id"
    ).fetchall()
    first_task_phase_ids = dict(
        conn.execute("SELECT id, phase_id FROM tasks ORDER BY id").fetchall()
    )
    conn.close()

    init_db(db_path)

    conn = sqlite3.connect(db_path)
    second_phase_rows = conn.execute(
        "SELECT id, project_id, title, status, order_index FROM phases ORDER BY id"
    ).fetchall()
    second_task_phase_ids = dict(
        conn.execute("SELECT id, phase_id FROM tasks ORDER BY id").fetchall()
    )
    conn.close()

    assert len(first_phase_rows) == 1
    assert first_phase_rows == second_phase_rows
    assert first_task_phase_ids == second_task_phase_ids
