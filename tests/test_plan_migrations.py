"""Regression tests for migrating legacy project-level plan state."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from engram.db import get_db_connection, init_db
from engram.models.project import Project
from engram.services.project_service import resolve_current_project


def _create_legacy_repo_db(
    repo_path: Path,
    *,
    project_id: str,
    name: str,
    plan_key: str | None = None,
    include_plan_key_column: bool = True,
) -> Path:
    """Create a legacy repo-local database shape for migration testing."""
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir()
    (repo_path / ".engram").mkdir()

    db_path = repo_path / ".engram" / "memory.db"
    conn = sqlite3.connect(db_path)
    if include_plan_key_column:
        conn.execute(
            """
            CREATE TABLE projects (
                id          TEXT PRIMARY KEY,
                plan_key    TEXT,
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
            INSERT INTO projects (id, plan_key, name, summary, status, repo_paths)
            VALUES (?, ?, ?, ?, 'active', '[]')
            """,
            (project_id, plan_key, name, None),
        )
    else:
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
            INSERT INTO projects (id, name, summary, status, repo_paths)
            VALUES (?, ?, ?, 'active', '[]')
            """,
            (project_id, name, None),
        )
    conn.commit()
    conn.close()
    return db_path


def test_init_db_backfills_explicit_project_plan_key_to_active_plan(tmp_path):
    repo_path = tmp_path / "explicit-plan"
    db_path = _create_legacy_repo_db(
        repo_path,
        project_id="legacy-proj-explicit",
        name="Legacy Explicit Project",
        plan_key="p0003",
    )

    init_db(db_path)
    init_db(db_path)

    conn = get_db_connection(db_path)
    try:
        plan_rows = conn.execute(
            "SELECT id, project_id, key, title, status FROM plans ORDER BY id"
        ).fetchall()
        project_row = conn.execute(
            "SELECT id, plan_key, active_plan_id FROM projects WHERE id = ?",
            ("legacy-proj-explicit",),
        ).fetchone()
    finally:
        conn.close()

    assert len(plan_rows) == 1
    plan_row = plan_rows[0]
    assert plan_row["project_id"] == "legacy-proj-explicit"
    assert plan_row["key"] == "p0003"
    assert plan_row["title"] == "Legacy Explicit Project"
    assert plan_row["status"] == "active"
    assert project_row is not None
    assert project_row["plan_key"] == "p0003"
    assert project_row["active_plan_id"] == plan_row["id"]

    project = Project.get("legacy-proj-explicit", db_path=db_path)
    assert project is not None
    assert project.active_plan_id == plan_row["id"]

    payload = resolve_current_project(cwd=str(repo_path))
    assert payload["id"] == "legacy-proj-explicit"
    assert payload["active_plan_id"] == plan_row["id"]
    assert payload["active_plan"]["id"] == plan_row["id"]
    assert payload["active_plan"]["key"] == "p0003"
    assert payload["active_plan"]["status"] == "active"


def test_init_db_leaves_fallback_project_key_unbound(tmp_path):
    repo_path = tmp_path / "fallback-plan"
    db_path = _create_legacy_repo_db(
        repo_path,
        project_id="legacy-proj-fallback",
        name="Legacy Fallback Project",
        include_plan_key_column=False,
    )

    init_db(db_path)

    conn = get_db_connection(db_path)
    try:
        project_row = conn.execute(
            "SELECT id, plan_key, active_plan_id FROM projects WHERE id = ?",
            ("legacy-proj-fallback",),
        ).fetchone()
        plan_count = conn.execute("SELECT COUNT(*) AS count FROM plans").fetchone()["count"]
    finally:
        conn.close()

    assert project_row is not None
    assert project_row["plan_key"] == "legacy-proj-fallback"
    assert project_row["active_plan_id"] is None
    assert plan_count == 0

    project = Project.get("legacy-proj-fallback", db_path=db_path)
    assert project is not None
    assert project.plan_key == "legacy-proj-fallback"
    assert project.active_plan_id is None

    payload = resolve_current_project(cwd=str(repo_path))
    assert payload["id"] == "legacy-proj-fallback"
    assert payload["active_plan_id"] is None
    assert payload["active_plan"] is None
