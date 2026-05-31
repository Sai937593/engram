"""Tests for project service read boundaries."""

from __future__ import annotations

import os

import pytest

from engram.services.errors import EngramServiceError
from engram.services.project_service import resolve_current_project
from engram.services.project_status_service import get_current_project_status


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


def test_initialize_project_creates_local_db_and_metadata(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    from engram.db import get_db_connection
    from engram.services.project_service import initialize_project

    payload = initialize_project(
        cwd=str(repo_path),
        name="Cool Project",
        project_id="cool-proj",
        summary="A summary of cool project",
    )

    assert payload["id"] == "cool-proj"
    assert payload["name"] == "Cool Project"
    assert payload["summary"] == "A summary of cool project"
    assert payload["repo_paths"] == [str(repo_path)]
    assert payload["created"] is True

    db_path = repo_path / ".engram" / "memory.db"
    assert db_path.exists()

    # Query the local DB directly to verify metadata row exists
    conn = get_db_connection(db_path)
    row = conn.execute("SELECT * FROM projects WHERE id = ?", ("cool-proj",)).fetchone()
    conn.close()

    assert row is not None
    assert row["name"] == "Cool Project"
    assert row["summary"] == "A summary of cool project"

    # Verify gitignore
    gitignore_path = repo_path / ".gitignore"
    assert gitignore_path.exists()
    assert ".engram/" in gitignore_path.read_text(encoding="utf-8")


def test_initialize_project_is_idempotent(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    from engram.services.project_service import initialize_project

    # First run
    payload1 = initialize_project(
        cwd=str(repo_path),
        name="Cool Project",
        project_id="cool-proj",
    )
    assert payload1["created"] is True

    # Second run
    payload2 = initialize_project(
        cwd=str(repo_path),
        name="Cool Project",
        project_id="cool-proj",
    )
    assert payload2["created"] is False
    assert payload2["id"] == "cool-proj"

    # Verify gitignore has exactly one entry
    gitignore_content = (repo_path / ".gitignore").read_text(encoding="utf-8")
    assert gitignore_content.count(".engram/") == 1


def test_append_to_gitignore_preserves_new_lines_and_whitespace(tmp_path):
    from engram.services.project_service import append_to_gitignore

    # Case 1: Existing file without trailing newline
    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text("*.log\n*.tmp", encoding="utf-8")

    append_to_gitignore(tmp_path)

    content = gitignore_path.read_text(encoding="utf-8")
    assert content == "*.log\n*.tmp\n.engram/\n"

    # Case 2: Existing file with trailing newline
    gitignore_path.write_text("*.log\n*.tmp\n", encoding="utf-8")

    append_to_gitignore(tmp_path)

    content = gitignore_path.read_text(encoding="utf-8")
    assert content == "*.log\n*.tmp\n.engram/\n"


def test_resolve_current_project_production_no_git(tmp_path):
    """Verify resolve_current_project raises PROJECT_NOT_BOUND in production mode when outside a git repo."""
    import sys
    from unittest.mock import patch

    cwd = tmp_path / "production_unbound"
    cwd.mkdir()

    with patch.dict(sys.modules):
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        with pytest.raises(EngramServiceError) as raised:
            resolve_current_project(cwd=str(cwd))
        assert raised.value.code == "PROJECT_NOT_BOUND"


def test_resolve_current_project_production_missing_engram(tmp_path):
    """Verify resolve_current_project raises PROJECT_NOT_BOUND in production mode when .git exists but .engram is missing."""
    import sys
    from unittest.mock import patch

    cwd = tmp_path / "production_unbound"
    cwd.mkdir()
    (cwd / ".git").mkdir()

    with patch.dict(sys.modules):
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        with pytest.raises(EngramServiceError) as raised:
            resolve_current_project(cwd=str(cwd))
        assert raised.value.code == "PROJECT_NOT_BOUND"


def test_resolve_current_project_production_missing_db(tmp_path):
    """Verify resolve_current_project raises PROJECT_NOT_BOUND in production mode when .git and .engram exist but DB is missing."""
    import sys
    from unittest.mock import patch

    cwd = tmp_path / "production_unbound"
    cwd.mkdir()
    (cwd / ".git").mkdir()
    (cwd / ".engram").mkdir()

    with patch.dict(sys.modules):
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        with pytest.raises(EngramServiceError) as raised:
            resolve_current_project(cwd=str(cwd))
        assert raised.value.code == "PROJECT_NOT_BOUND"


def test_resolve_current_project_production_empty_db(tmp_path):
    """Verify resolve_current_project raises PROJECT_NOT_BOUND in production mode when DB is present but empty."""
    import sys
    from unittest.mock import patch

    from engram.db import init_db

    cwd = tmp_path / "production_unbound"
    cwd.mkdir()
    (cwd / ".git").mkdir()
    (cwd / ".engram").mkdir()

    db_path = cwd / ".engram" / "memory.db"
    init_db(db_path)

    with patch.dict(sys.modules):
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        with pytest.raises(EngramServiceError) as raised:
            resolve_current_project(cwd=str(cwd))
        assert raised.value.code == "PROJECT_NOT_BOUND"


def test_resolve_current_project_production_corrupted_db(tmp_path):
    """Verify resolve_current_project raises PROJECT_NOT_BOUND in production mode when DB is corrupted."""
    import sys
    from unittest.mock import patch

    cwd = tmp_path / "production_unbound"
    cwd.mkdir()
    (cwd / ".git").mkdir()
    (cwd / ".engram").mkdir()

    db_path = cwd / ".engram" / "memory.db"
    db_path.write_text("not a sqlite database", encoding="utf-8")

    with patch.dict(sys.modules):
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        with pytest.raises(EngramServiceError) as raised:
            resolve_current_project(cwd=str(cwd))
        assert raised.value.code == "PROJECT_NOT_BOUND"


def test_resolve_current_project_test_fallback_success(tmp_db, tmp_path):
    """Verify resolve_current_project successfully uses find_by_repo_path fallback in test environment."""
    from engram.models.project import Project

    cwd = str((tmp_path / "legacy_path").resolve())

    Project.create(
        id="legacy-fallback-proj",
        name="Legacy Fallback Project",
        summary="A legacy fallback project",
        repo_paths=[cwd],
    )

    payload = resolve_current_project(cwd=cwd)

    assert payload["id"] == "legacy-fallback-proj"
    assert payload["name"] == "Legacy Fallback Project"
    assert cwd in payload["repo_paths"]


def test_resolve_current_project_test_fallback_no_match(tmp_db, tmp_path):
    """Verify resolve_current_project raises PROJECT_NOT_BOUND in test environment when fallback doesn't match."""
    cwd = str((tmp_path / "unbound_path").resolve())

    with pytest.raises(EngramServiceError) as raised:
        resolve_current_project(cwd=cwd)
    assert raised.value.code == "PROJECT_NOT_BOUND"


def test_get_current_project_status_returns_ready_for_initialized_repo(tmp_path):
    repo_path = tmp_path / "repo_status_ready"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    (repo_path / ".engram").mkdir()

    from engram.db import get_db_connection, init_db

    db_path = repo_path / ".engram" / "memory.db"
    init_db(db_path)

    conn = get_db_connection(db_path)
    conn.execute(
        "INSERT INTO projects (id, name, summary, status, repo_paths) VALUES (?, ?, ?, ?, ?)",
        ("proj-status", "Status Project", "Project status", "active", "[]"),
    )
    conn.commit()
    conn.close()

    payload = get_current_project_status(cwd=str(repo_path))
    assert payload["initialized"] is True
    assert payload["status"] == "ready"
    assert payload["db_exists"] is True
    assert payload["project"]["id"] == "proj-status"


def test_get_current_project_status_returns_uninitialized_for_repo_without_db(tmp_path):
    repo_path = tmp_path / "repo_status_uninit"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    payload = get_current_project_status(cwd=str(repo_path))
    assert payload["initialized"] is False
    assert payload["status"] == "uninitialized"
    assert payload["db_exists"] is False
    assert "engram_project_init" in str(payload["next_action"])
