"""Tests for Task model including status lifecycle and priority ordering."""

import sqlite3

from engram.db import get_db_connection, init_db
from engram.models.phase import Phase
from engram.models.task import Task, _normalize_relevant_files, get_effective_phase_title


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


def test_create_task_with_relevant_files_normalizes_and_persists(project, tmp_db):
    t = Task.create(
        project_id=project.id,
        title="Task with relevant files",
        relevant_files=[
            " src/engram/models/task.py ",
            "",
            "tests/test_task.py",
            "src/engram/models/task.py",
            "   ",
            "tests/test_task.py",
        ],
    )
    assert t.relevant_files == ["src/engram/models/task.py", "tests/test_task.py"]

    conn = get_db_connection(tmp_db)
    row = conn.execute("SELECT relevant_files FROM tasks WHERE id = ?", (t.id,)).fetchone()
    conn.close()

    assert row["relevant_files"] == '["src/engram/models/task.py", "tests/test_task.py"]'


def test_normalize_relevant_files_deduplicates_preserve_first_seen_order():
    assert _normalize_relevant_files(
        [" src/a.py ", "src/a.py", "", "tests/b.py", "tests/b.py"]
    ) == [
        "src/a.py",
        "tests/b.py",
    ]


def test_task_from_row_deserializes_invalid_json_relevant_files():
    """Verify that _deserialize_relevant_files falls back to comma-split for non-JSON strings."""
    row = {
        "id": "t-1",
        "project_id": "p-1",
        "title": "Title",
        "description": "Desc",
        "status": "todo",
        "priority": "medium",
        "phase": None,
        "phase_id": None,
        "depends_on": None,
        "acceptance": None,
        "evidence": None,
        "tags": "",
        "relevant_files": "src/a.py, tests/b.py ,src/a.py",
    }

    t = Task.from_row(row)
    assert t.relevant_files == ["src/a.py", "tests/b.py"]


def test_task_from_row_deserializes_valid_json_relevant_files():
    """Verify that _deserialize_relevant_files loads JSON arrays."""
    row = {
        "id": "t-1",
        "project_id": "p-1",
        "title": "Title",
        "description": "Desc",
        "status": "todo",
        "priority": "medium",
        "phase": None,
        "phase_id": None,
        "depends_on": None,
        "acceptance": None,
        "evidence": None,
        "tags": "",
        "relevant_files": '["src/a.py", "tests/b.py"]',
    }

    t = Task.from_row(row)
    assert t.relevant_files == ["src/a.py", "tests/b.py"]


def test_task_from_row_deserializes_none_relevant_files():
    """Verify that _deserialize_relevant_files handles None correctly."""
    row = {
        "id": "t-1",
        "project_id": "p-1",
        "title": "Title",
        "description": "Desc",
        "status": "todo",
        "priority": "medium",
        "phase": None,
        "phase_id": None,
        "depends_on": None,
        "acceptance": None,
        "evidence": None,
        "tags": "",
        "relevant_files": None,
    }

    t = Task.from_row(row)
    assert t.relevant_files == []


def test_create_task_persists_phase_id_without_legacy_phase(project, tmp_db):
    t = Task.create(project_id=project.id, title="Task with phase id", phase_id="phase-123")
    assert t.phase is None
    assert t.phase_id == "phase-123"

    conn = get_db_connection(tmp_db)
    row = conn.execute("SELECT phase, phase_id FROM tasks WHERE id = ?", (t.id,)).fetchone()
    conn.close()

    assert row["phase"] is None
    assert row["phase_id"] == "phase-123"


def test_create_task_with_legacy_phase_remains_compatible(project, tmp_db):
    t = Task.create(project_id=project.id, title="Legacy phase task", phase="Phase Alpha")

    conn = get_db_connection(tmp_db)
    row = conn.execute("SELECT phase, phase_id FROM tasks WHERE id = ?", (t.id,)).fetchone()
    conn.close()

    assert t.phase == "Phase Alpha"
    assert t.phase_id is None
    assert row["phase"] == "Phase Alpha"
    assert row["phase_id"] is None


def test_get_task(task):
    fetched = Task.get(task.id)
    assert fetched is not None
    assert fetched.title == task.title


def test_get_task_defaults_relevant_files_to_empty_list(task):
    fetched = Task.get(task.id)
    assert fetched is not None
    assert fetched.relevant_files == []


def test_get_nonexistent_task(tmp_db):
    assert Task.get("no-such-id") is None


def test_list_by_project(project):
    Task.create(project_id=project.id, title="Task A")
    Task.create(project_id=project.id, title="Task B")
    tasks = Task.list_by_project(project.id)
    titles = [t.title for t in tasks]
    assert "Task A" in titles
    assert "Task B" in titles


def test_list_by_project_round_trips_relevant_files(project):
    task_a = Task.create(
        project_id=project.id,
        title="Task A",
        relevant_files=["src/engram/db_helpers/schema.py"],
    )
    task_b = Task.create(project_id=project.id, title="Task B")
    tasks = {t.id: t for t in Task.list_by_project(project.id)}

    assert tasks[task_a.id].relevant_files == ["src/engram/db_helpers/schema.py"]
    assert tasks[task_b.id].relevant_files == []


def test_count_by_status_empty(tmp_db, project):
    """count_by_status returns empty dict when no tasks exist."""
    counts = Task.count_by_status(project.id)
    assert counts == {}


def test_count_by_status_mixed(tmp_db, project):
    """count_by_status returns accurate counts across statuses."""
    Task.create(project_id=project.id, title="A", status="todo")
    Task.create(project_id=project.id, title="B", status="todo")
    Task.create(project_id=project.id, title="C", status="done")
    Task.create(project_id=project.id, title="D", status="blocked")

    counts = Task.count_by_status(project.id)
    assert counts["todo"] == 2
    assert counts["done"] == 1
    assert counts["blocked"] == 1


def test_update_task_status(task):
    task.update(status="in-progress")
    refreshed = Task.get(task.id)
    assert refreshed.status == "in-progress"


def test_update_task_evidence(task):
    task.update(evidence="All tests passed.")
    refreshed = Task.get(task.id)
    assert refreshed.evidence == "All tests passed."


def test_update_task_phase_id(task):
    task.update(phase_id="phase-updated")
    refreshed = Task.get(task.id)
    assert refreshed.phase_id == "phase-updated"


def test_update_task_relevant_files_normalizes(task):
    task.update(
        relevant_files=[
            " src/engram/models/task.py ",
            "",
            "tests/conftest.py",
            "src/engram/models/task.py",
        ]
    )
    refreshed = Task.get(task.id)
    assert refreshed.relevant_files == ["src/engram/models/task.py", "tests/conftest.py"]


def test_get_effective_phase_title_for_future_branch_labels_prefers_first_class_phase(project):
    phase = Phase.create(project_id=project.id, title="Phase Roadmap")
    task = Task.create(
        project_id=project.id,
        title="Task with both phase fields",
        phase="Legacy Phase Text",
        phase_id=phase.id,
    )

    assert get_effective_phase_title(task) == "Phase Roadmap"


def test_get_effective_phase_title_for_future_commit_scopes_falls_back_to_legacy_phase(project):
    task = Task.create(
        project_id=project.id,
        title="Legacy phase task",
        phase="Phase Legacy",
        phase_id=None,
    )

    assert get_effective_phase_title(task) == "Phase Legacy"


def test_get_effective_phase_title_returns_none_for_unphased_task(project):
    task = Task.create(project_id=project.id, title="Unphased task", phase=None, phase_id=None)

    assert get_effective_phase_title(task) is None


def test_get_effective_phase_title_handles_stale_phase_id_with_no_legacy_phase(project):
    task = Task.create(
        project_id=project.id,
        title="Stale phase pointer",
        phase=None,
        phase_id="missing-phase-id",
    )

    assert get_effective_phase_title(task) is None


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
    assert "relevant_files" in task_columns


def test_init_db_backfills_legacy_task_phase_strings(tmp_path) -> None:
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
        "INSERT INTO projects (id, name, repo_paths) VALUES ('legacy-proj-1', 'Legacy 1', '[]')"
    )
    legacy_conn.execute(
        "INSERT INTO projects (id, name, repo_paths) VALUES ('legacy-proj-2', 'Legacy 2', '[]')"
    )
    legacy_conn.execute(
        """
        INSERT INTO tasks (id, project_id, title, status, phase)
        VALUES ('legacy-task-1', 'legacy-proj-1', 'Legacy Task 1', 'todo', ' Phase Alpha ')
        """
    )
    legacy_conn.execute(
        """
        INSERT INTO tasks (id, project_id, title, status, phase)
        VALUES ('legacy-task-2', 'legacy-proj-1', 'Legacy Task 2', 'todo', 'phase   alpha')
        """
    )
    legacy_conn.execute(
        """
        INSERT INTO tasks (id, project_id, title, status, phase)
        VALUES ('legacy-task-3', 'legacy-proj-1', 'Legacy Task 3', 'todo', '')
        """
    )
    legacy_conn.execute(
        """
        INSERT INTO tasks (id, project_id, title, status, phase)
        VALUES ('legacy-task-4', 'legacy-proj-1', 'Legacy Task 4', 'todo', NULL)
        """
    )
    legacy_conn.execute(
        """
        INSERT INTO tasks (id, project_id, title, status, phase)
        VALUES ('legacy-task-5', 'legacy-proj-2', 'Legacy Task 5', 'todo', 'Phase Alpha')
        """
    )
    legacy_conn.execute(
        """
        INSERT INTO tasks (id, project_id, title, status, phase)
        VALUES ('legacy-task-6', 'legacy-proj-2', 'Legacy Task 6', 'todo', 'Phase Beta')
        """
    )
    legacy_conn.commit()
    legacy_conn.close()

    init_db(db_path)
    init_db(db_path)

    conn = get_db_connection(db_path)
    task_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    phase_columns = {row["name"] for row in conn.execute("PRAGMA table_info(phases)").fetchall()}
    phase_rows = conn.execute(
        """
        SELECT project_id, title
        FROM phases
        ORDER BY project_id, title
        """
    ).fetchall()
    phase_ids = dict(conn.execute("SELECT id, project_id || ':' || title FROM phases").fetchall())
    task_phase_rows = dict(
        conn.execute("SELECT id, phase_id FROM tasks WHERE id LIKE 'legacy-task-%'").fetchall()
    )
    task_legacy_phase_rows = dict(
        conn.execute(
            "SELECT id, phase FROM tasks WHERE id IN ('legacy-task-1', 'legacy-task-2')"
        ).fetchall()
    )
    conn.close()

    assert "phase_id" in task_columns
    assert "relevant_files" in task_columns
    assert {"project_id", "title", "status", "order_index"}.issubset(phase_columns)
    assert len(phase_rows) == 3
    assert [tuple(row) for row in phase_rows] == [
        ("legacy-proj-1", "Phase Alpha"),
        ("legacy-proj-2", "Phase Alpha"),
        ("legacy-proj-2", "Phase Beta"),
    ]
    assert task_phase_rows["legacy-task-1"] == task_phase_rows["legacy-task-2"]
    assert task_phase_rows["legacy-task-1"] != task_phase_rows["legacy-task-5"]
    assert task_phase_rows["legacy-task-3"] is None
    assert task_phase_rows["legacy-task-4"] is None
    assert task_phase_rows["legacy-task-5"] is not None
    assert task_phase_rows["legacy-task-6"] is not None
    assert task_legacy_phase_rows["legacy-task-1"] == " Phase Alpha "
    assert task_legacy_phase_rows["legacy-task-2"] == "phase   alpha"
    assert all(phase_id for phase_id in phase_ids.keys())


def test_init_db_legacy_tasks_default_relevant_files_to_empty_list(tmp_path) -> None:
    db_path = tmp_path / "legacy_relevant_files.db"
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
        "INSERT INTO tasks (id, project_id, title, status) VALUES ('legacy-task', 'legacy-proj', 'Legacy task', 'todo')"
    )
    legacy_conn.commit()
    legacy_conn.close()

    init_db(db_path)

    conn = get_db_connection(db_path)
    task_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    task_row = conn.execute("SELECT * FROM tasks WHERE id = 'legacy-task'").fetchone()
    conn.close()
    assert "relevant_files" in task_columns

    task = Task.from_row(task_row) if task_row else None
    assert task is not None
    assert task.relevant_files == []


def test_get_next_prefer_active_phase(project):
    phase_1 = Phase.create(project_id=project.id, title="Phase 1")
    phase_2 = Phase.create(project_id=project.id, title="Phase 2")

    task_p1 = Task.create(
        project_id=project.id,
        title="Task Phase 1",
        priority="medium",
        phase_id=phase_1.id,
    )
    task_p2 = Task.create(
        project_id=project.id,
        title="Task Phase 2",
        priority="high",
        phase_id=phase_2.id,
    )

    nxt = Task.get_next(project.id, active_phase_id=phase_1.id)
    assert nxt is not None
    assert nxt.id == task_p1.id

    nxt = Task.get_next(project.id, active_phase_id=phase_2.id)
    assert nxt is not None
    assert nxt.id == task_p2.id

    nxt = Task.get_next(project.id)
    assert nxt is not None
    assert nxt.id == task_p2.id


def test_get_next_active_phase_fallback_to_project_level(project):
    phase_1 = Phase.create(project_id=project.id, title="Phase 1")

    task_proj = Task.create(
        project_id=project.id,
        title="Project Level Task",
        priority="medium",
        phase_id=None,
    )

    nxt = Task.get_next(project.id, active_phase_id=phase_1.id)
    assert nxt is not None
    assert nxt.id == task_proj.id
