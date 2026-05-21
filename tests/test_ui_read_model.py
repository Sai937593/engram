"""Tests for the read-only UI query layer."""

from engram.db import get_db_connection
from engram.models.memory import Memory
from engram.models.task import Task
from engram.ui import read_model


def test_dashboard_snapshot_groups_current_project_state(project):
    """Dashboard read model returns dense project state without writes."""
    task = Task.create(project_id=project.id, title="Inspect UI", status="in-progress")
    Memory.create(project_id=project.id, type="lesson", title="Live UI", content="Poll DB")

    dashboard = read_model.get_dashboard(project.id)

    assert dashboard["project"]["id"] == project.id
    assert dashboard["task_counts"]["in-progress"] == 1
    assert dashboard["active_tasks"][0]["id"] == task.id
    assert dashboard["memory_counts"]["lesson"] == 1


def test_snapshot_version_changes_when_project_rows_change(project, task):
    """Snapshot version advances from row update timestamps."""
    before = read_model.get_snapshot_version(project.id)

    conn = get_db_connection()
    conn.execute("UPDATE tasks SET updated_at = '2099-01-01 00:00:00' WHERE id = ?", (task.id,))
    conn.commit()
    conn.close()

    after = read_model.get_snapshot_version(project.id)

    assert after != before
    assert after == "2099-01-01 00:00:00"


def test_audit_events_are_scoped_to_project(project):
    """Audit read model only returns events for rows owned by the project."""
    task = Task.create(project_id=project.id, title="Scoped task")

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO audit_log (target_table, target_id, operation) VALUES ('tasks', 'other', 'create')"
    )
    conn.commit()
    conn.close()

    events = read_model.list_audit_events(project.id)

    assert any(event["target_id"] == task.id for event in events)
    assert all(event["target_id"] != "other" for event in events)
