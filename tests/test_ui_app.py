"""Route tests for the read-only Engram UI."""

from fastapi.testclient import TestClient

from engram.db import get_db_connection
from engram.models.memory import Memory
from engram.models.project import Project
from engram.models.task import Task
from engram.ui.app import create_app
from engram.ui.state import UiTarget, write_target


def _target(project, repo_path="/tmp/test", version="2026-01-01T00:00:00+00:00"):
    return UiTarget(
        project_id=project.id,
        project_name=project.name,
        repo_path=repo_path,
        version=version,
        updated_at=version,
    )


def test_ui_pages_render_project_data(project, tmp_path):
    """API endpoints render seeded project data."""
    state_path = tmp_path / "ui_state.json"
    write_target(_target(project), state_path)
    task = Task.create(project_id=project.id, title="Render tasks", status="in-progress")
    memory = Memory.create(
        project_id=project.id, type="decision", title="Render memory", content="x"
    )
    client = TestClient(create_app(state_path))

    endpoints = {
        "/api/dashboard": project.name,
        "/api/tasks": task.title,
        "/api/memories": memory.title,
        "/api/audit": task.id,
    }

    for path, expected in endpoints.items():
        response = client.get(path)
        assert response.status_code == 200
        assert expected in response.text


def test_snapshot_version_endpoint_reflects_db_changes(project, task, tmp_path):
    """Polling endpoint returns a new token after DB state changes."""
    state_path = tmp_path / "ui_state.json"
    write_target(_target(project), state_path)
    client = TestClient(create_app(state_path))
    before = client.get("/api/snapshot-version").json()["version"]

    conn = get_db_connection()
    conn.execute("UPDATE tasks SET updated_at = '2099-02-01 00:00:00' WHERE id = ?", (task.id,))
    conn.commit()
    conn.close()

    after = client.get("/api/snapshot-version").json()["version"]

    assert after != before
    assert after == "2099-02-01 00:00:00"


def test_snapshot_version_endpoint_reflects_ui_target_changes(project, tmp_path):
    """Polling endpoint changes when another project becomes the active UI target."""
    state_path = tmp_path / "ui_state.json"
    other = Project.create("other-proj", "Other Project", repo_paths=["/tmp/other"])
    write_target(_target(project, version="2099-01-01T00:00:00+00:00"), state_path)
    client = TestClient(create_app(state_path))

    before = client.get("/api/snapshot-version").json()
    write_target(_target(other, "/tmp/other", "2099-01-01T00:00:01+00:00"), state_path)
    after = client.get("/api/snapshot-version").json()

    assert before["project_id"] == project.id
    assert after["project_id"] == other.id
    assert after["version"] != before["version"]


def test_existing_ui_routes_switch_when_state_changes(project, tmp_path):
    """An already-created app reads the latest UI state on each request."""
    state_path = tmp_path / "ui_state.json"
    other = Project.create("switch-proj", "Switch Project", repo_paths=["/tmp/switch"])
    write_target(_target(project), state_path)
    client = TestClient(create_app(state_path))

    assert project.name in client.get("/api/ui-state").text

    write_target(_target(other, "/tmp/switch", "2026-01-01T00:00:02+00:00"), state_path)

    response = client.get("/api/ui-state")
    assert response.status_code == 200
    assert other.name in response.text
    assert project.name not in response.text


def test_ui_unknown_ids_return_404(project, tmp_path):
    """Detail mutation routes are scoped and return 404 for missing records."""
    state_path = tmp_path / "ui_state.json"
    write_target(_target(project), state_path)
    client = TestClient(create_app(state_path))

    assert client.patch("/api/tasks/missing/status", json={"status": "done"}).status_code == 404
    assert client.patch("/api/memories/missing", json={"title": "new"}).status_code == 404


def test_ui_routes_allow_mutations(project, tmp_path):
    """Mutation methods work for tasks."""
    state_path = tmp_path / "ui_state.json"
    write_target(_target(project), state_path)
    client = TestClient(create_app(state_path))
    task = Task.create(project_id=project.id, title="Update me")

    res = client.patch(f"/api/tasks/{task.id}/status", json={"status": "in-progress"})
    assert res.status_code == 200
    assert res.json()["task"]["status"] == "in-progress"
