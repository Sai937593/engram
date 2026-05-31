"""Tests for project service read boundaries."""

from __future__ import annotations

import os

import pytest

from engram.services.errors import EngramServiceError
from engram.services.project_service import resolve_current_project


def test_resolve_current_project_returns_serialized_project_for_bound_repo(tmp_path):
    repo_path = tmp_path / "repo_bound"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    (repo_path / ".engram").mkdir()

    from engram.db import get_db_connection, init_db

    db_path = repo_path / ".engram" / "memory.db"
    init_db(db_path)

    conn = get_db_connection(db_path)
    conn.execute(
        "INSERT INTO projects (id, name, summary, status, repo_paths) VALUES (?, ?, ?, ?, ?)",
        ("proj1234", "Bound Project", "Service test project", "active", "[]"),
    )
    conn.commit()
    conn.close()

    payload = resolve_current_project(cwd=str(repo_path))

    assert payload == {
        "id": "proj1234",
        "name": "Bound Project",
        "summary": "Service test project",
        "status": "active",
        "repo_paths": [str(repo_path)],
    }


def test_resolve_current_project_raises_project_not_bound_for_unbound_repo(tmp_path):
    # Case 1: No .git directory at all
    cwd = tmp_path / "repo_unbound"
    cwd.mkdir()

    with pytest.raises(EngramServiceError) as raised:
        resolve_current_project(cwd=str(cwd))
    error = raised.value
    assert error.code == "PROJECT_NOT_BOUND"

    # Case 2: .git directory exists but no .engram/memory.db
    (cwd / ".git").mkdir()
    with pytest.raises(EngramServiceError) as raised:
        resolve_current_project(cwd=str(cwd))
    error = raised.value
    assert error.code == "PROJECT_NOT_BOUND"


def test_resolve_current_project_uses_os_getcwd_when_cwd_is_omitted(tmp_path, monkeypatch):
    repo_path = tmp_path / "repo_cwd"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    (repo_path / ".engram").mkdir()

    from engram.db import get_db_connection, init_db

    db_path = repo_path / ".engram" / "memory.db"
    init_db(db_path)

    conn = get_db_connection(db_path)
    conn.execute(
        "INSERT INTO projects (id, name, summary, status, repo_paths) VALUES (?, ?, ?, ?, ?)",
        ("proj-cwd", "Cwd Project", None, "active", "[]"),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(os, "getcwd", lambda: str(repo_path))

    payload = resolve_current_project()

    assert payload["id"] == "proj-cwd"
    assert payload["name"] == "Cwd Project"
    assert payload["repo_paths"] == [str(repo_path)]


def test_find_repo_root_success(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    nested_dir = tmp_path / "sub" / "nested"
    nested_dir.mkdir(parents=True)

    from engram.services.project_path import find_repo_root

    # 1. From root
    root = find_repo_root(cwd=str(tmp_path))
    assert root == tmp_path

    # 2. From nested folder
    root_nested = find_repo_root(cwd=str(nested_dir))
    assert root_nested == tmp_path


def test_find_repo_root_raises_unresolved_workspace(tmp_path):
    nested_dir = tmp_path / "sub" / "nested"
    nested_dir.mkdir(parents=True)

    from engram.services.project_path import find_repo_root

    with pytest.raises(EngramServiceError) as raised:
        find_repo_root(cwd=str(nested_dir))

    error = raised.value
    assert error.code == "UNRESOLVED_WORKSPACE"
    assert "Could not resolve repository root" in error.message
    assert error.details["cwd"] == str(nested_dir.resolve())


def test_local_state_paths_derivation(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    nested_dir = tmp_path / "sub" / "nested"
    nested_dir.mkdir(parents=True)

    from engram.services.project_path import get_repo_local_db_path, get_repo_local_engram_dir

    engram_dir = get_repo_local_engram_dir(cwd=str(nested_dir))
    assert engram_dir == tmp_path / ".engram"

    db_path = get_repo_local_db_path(cwd=str(nested_dir))
    assert db_path == tmp_path / ".engram" / "memory.db"
