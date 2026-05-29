"""Tests to verify NULL safety in the Project model."""

from engram.db import get_db_connection
from engram.models.project import Project


def test_project_null_safety_in_get_find_list(tmp_db):
    # Manually insert a project with NULL repo_paths column
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO projects (id, name, summary, repo_paths) VALUES (?, ?, ?, ?)",
        ("null-paths-proj", "Null Paths Project", "A project with null paths", None),
    )
    conn.commit()
    conn.close()

    # Test Project.get handles NULL repo_paths
    p = Project.get("null-paths-proj")
    assert p is not None
    assert p.id == "null-paths-proj"
    assert p.name == "Null Paths Project"
    assert p.repo_paths == []

    # Test Project.find_by_repo_path does not crash on projects with NULL paths
    p_found = Project.find_by_repo_path("/some/random/path")
    assert p_found is None

    # Test Project.list_all handles NULL repo_paths
    all_projects = Project.list_all()
    p_in_list = next((proj for proj in all_projects if proj.id == "null-paths-proj"), None)
    assert p_in_list is not None
    assert p_in_list.repo_paths == []
