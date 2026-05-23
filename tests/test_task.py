"""Tests for Task model including status lifecycle and priority ordering."""

import sqlite3

from engram.db import get_db_connection, init_db
from engram.models.task import Task


def test_create_task(project):
    t = Task.create(project_id=project.id, title="Write tests", priority="high")
    assert t.title == "Write tests"
    assert t.status == "todo"
    assert t.priority == "high"
    assert t.tags == []


def test_create_task_with_tags(project):
    t = Task.create(project_id=project.id, title="Tagged task", tags=["ci", "testing"])
    assert "ci" in t.tags
    assert "testing" in t.tags


def test_get_task(task):
    fetched = Task.get(task.id)
    assert fetched is not None
    assert fetched.title == task.title


def test_get_nonexistent_task(tmp_db):
    assert Task.get("no-such-id") is None


def test_list_by_project(project):
    Task.create(project_id=project.id, title="Task A")
    Task.create(project_id=project.id, title="Task B")
    tasks = Task.list_by_project(project.id)
    titles = [t.title for t in tasks]
    assert "Task A" in titles
    assert "Task B" in titles


def test_update_task_status(task):
    task.update(status="in-progress")
    refreshed = Task.get(task.id)
    assert refreshed.status == "in-progress"


def test_update_task_evidence(task):
    task.update(evidence="All tests passed.")
    refreshed = Task.get(task.id)
    assert refreshed.evidence == "All tests passed."


def test_get_next_respects_priority(project):
    Task.create(project_id=project.id, title="Low priority task", priority="low")
    Task.create(project_id=project.id, title="Critical task", priority="critical")
    Task.create(project_id=project.id, title="High priority task", priority="high")
    nxt = Task.get_next(project.id)
    assert nxt.priority == "critical"


def test_get_next_skips_non_todo(project):
    t = Task.create(project_id=project.id, title="Done task", priority="critical")
    t.update(status="done")
    Task.create(project_id=project.id, title="Todo task", priority="low")
    nxt = Task.get_next(project.id)
    assert nxt.title == "Todo task"


def test_get_next_returns_none_when_empty(project):
    assert Task.get_next(project.id) is None


def test_delete_task(task):
    task.delete()
    assert Task.get(task.id) is None


def test_db_migration_completed_to_done(tmp_db):
    """Verify the completed → done migration runs correctly."""
    from engram.models.project import Project

    p = Project.create("mig-proj", "Mig Project", repo_paths=["/tmp/mig"])
    # Manually insert a task with legacy 'completed' status
    conn = get_db_connection(tmp_db)
    conn.execute(
        "INSERT INTO tasks (id, project_id, title, status) VALUES ('t-legacy', ?, 'Legacy', 'completed')",
        (p.id,),
    )
    conn.commit()
    conn.close()
    # Re-run init_db to trigger the migration
    init_db(tmp_db)
    t = Task.get("t-legacy")
    assert t.status == "done"


def test_init_db_creates_phases_schema(tmp_db) -> None:
    conn = get_db_connection(tmp_db)
    phase_columns = {row["name"] for row in conn.execute("PRAGMA table_info(phases)").fetchall()}
    task_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    conn.close()

    assert {
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
    }.issubset(phase_columns)
    assert "phase_id" in task_columns


def test_init_db_migrates_legacy_tasks_with_no_phase_id(tmp_path, monkeypatch) -> None:
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
    legacy_conn.execute(
        "INSERT INTO projects (id, name, repo_paths) VALUES ('legacy-proj', 'Legacy', '[]')"
    )
    legacy_conn.execute(
        """
        INSERT INTO tasks (id, project_id, title, status, phase)
        VALUES ('legacy-task', 'legacy-proj', 'Legacy Task', 'todo', 'Phase Alpha')
        """
    )
    legacy_conn.commit()
    legacy_conn.close()

    init_db(db_path)
    init_db(db_path)

    monkeypatch.setattr("engram.models.task.get_db_connection", lambda: get_db_connection(db_path))
    task = Task.get("legacy-task")
    assert task is not None
    assert task.title == "Legacy Task"
    assert task.phase == "Phase Alpha"

    conn = get_db_connection(db_path)
    task_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    phase_columns = {row["name"] for row in conn.execute("PRAGMA table_info(phases)").fetchall()}
    phase_id = conn.execute("SELECT phase_id FROM tasks WHERE id = 'legacy-task'").fetchone()[0]
    conn.close()

    assert "phase_id" in task_columns
    assert {"project_id", "title", "status", "order_index"}.issubset(phase_columns)
    assert phase_id is None
