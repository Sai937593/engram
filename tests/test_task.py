"""Tests for Task model including status lifecycle and priority ordering."""

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
    from engram.db import get_db_connection
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
    from engram.db import init_db

    init_db(tmp_db)
    t = Task.get("t-legacy")
    assert t.status == "done"
