"""Tests for Project model CRUD operations."""

from engram.models.project import Project


def test_create_project(tmp_db):
    p = Project.create("my-proj", "My Project", summary="A summary", repo_paths=["/tmp/repo"])
    assert p.id == "my-proj"
    assert p.name == "My Project"
    assert p.summary == "A summary"
    assert p.status == "active"
    assert "/tmp/repo" in p.repo_paths


def test_get_project(tmp_db):
    Project.create("get-proj", "Get Project")
    p = Project.get("get-proj")
    assert p is not None
    assert p.name == "Get Project"


def test_get_nonexistent_project(tmp_db):
    assert Project.get("does-not-exist") is None


def test_find_by_repo_path(tmp_db):
    import os

    repo_path = os.path.abspath("/tmp/myrepo")
    Project.create("path-proj", "Path Project", repo_paths=[repo_path])
    p = Project.find_by_repo_path(repo_path)
    assert p is not None
    assert p.id == "path-proj"


def test_find_by_repo_path_not_found(tmp_db):
    assert Project.find_by_repo_path("/tmp/nonexistent") is None


def test_list_all_projects(tmp_db):
    Project.create("proj-a", "Project A")
    Project.create("proj-b", "Project B")
    projects = Project.list_all()
    ids = [p.id for p in projects]
    assert "proj-a" in ids
    assert "proj-b" in ids


def test_update_project(project):
    project.update(name="Updated Name", summary="New summary", status="paused")
    refreshed = Project.get(project.id)
    assert refreshed.name == "Updated Name"
    assert refreshed.summary == "New summary"
    assert refreshed.status == "paused"


def test_add_repo_path(project):
    import os

    new_path = os.path.abspath("/tmp/another-repo")
    project.add_repo_path(new_path)
    refreshed = Project.get(project.id)
    assert new_path in refreshed.repo_paths
