"""Tests for Project model NULL safety."""

from __future__ import annotations

from engram.db import get_db_connection
from engram.models.project import Project


def test_project_null_safety(tmp_db):
    """Verify that Project methods do not crash when repo_paths is NULL."""
    # Insert a project manually with a NULL repo_paths value
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO projects (id, name, summary, repo_paths) VALUES (?, ?, ?, NULL)",
        ("null-proj", "Null Project", "A project with null repo paths"),
    )
    conn.commit()
    conn.close()

    # Test Project.get
    project = Project.get("null-proj")
    assert project is not None
    assert project.id == "null-proj"
    assert project.repo_paths == []

    # Test Project.find_by_repo_path
    # Since repo_paths is NULL, it should not find the project for any path, but it should not crash!
    found = Project.find_by_repo_path("/some/path")
    assert found is None

    # Test Project.list_all
    all_projects = Project.list_all()
    null_proj_list = [p for p in all_projects if p.id == "null-proj"]
    assert len(null_proj_list) == 1
    assert null_proj_list[0].repo_paths == []
