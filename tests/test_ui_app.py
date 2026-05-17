"""Route tests for the read-only Engram UI."""

from fastapi.testclient import TestClient

from engram.db import get_db_connection
from engram.models.memory import Memory
from engram.models.session import Session
from engram.models.task import Task
from engram.ui.app import create_app


def test_ui_pages_render_project_data(project):
    """Core read-only pages render seeded project data."""
    task = Task.create(project_id=project.id, title="Render tasks", status="in-progress")
    memory = Memory.create(
        project_id=project.id, type="decision", title="Render memory", content="x"
    )
    session = Session.create(project_id=project.id, goal="Render session")
    client = TestClient(create_app(project.id))

    pages = {
        "/": project.name,
        "/tasks": task.title,
        f"/tasks/{task.id}": task.title,
        "/memories": memory.title,
        f"/memories/{memory.id}": memory.title,
        "/sessions": session.goal,
        f"/sessions/{session.id}": session.goal,
        "/audit": task.id,
    }

    for path, expected in pages.items():
        response = client.get(path)
        assert response.status_code == 200
        assert expected in response.text


def test_snapshot_version_endpoint_reflects_db_changes(project, task):
    """Polling endpoint returns a new token after DB state changes."""
    client = TestClient(create_app(project.id))
    before = client.get("/api/snapshot-version").json()["version"]

    conn = get_db_connection()
    conn.execute("UPDATE tasks SET updated_at = '2099-02-01 00:00:00' WHERE id = ?", (task.id,))
    conn.commit()
    conn.close()

    after = client.get("/api/snapshot-version").json()["version"]

    assert after != before
    assert after == "2099-02-01 00:00:00"


def test_ui_unknown_ids_return_404(project):
    """Detail routes are scoped and return 404 for missing records."""
    client = TestClient(create_app(project.id))

    assert client.get("/tasks/missing").status_code == 404
    assert client.get("/memories/missing").status_code == 404
    assert client.get("/sessions/missing").status_code == 404


def test_ui_routes_are_read_only(project):
    """Mutation methods are not exposed by the UI."""
    client = TestClient(create_app(project.id))

    assert client.post("/tasks").status_code == 405
    assert client.post("/api/snapshot-version").status_code == 405
