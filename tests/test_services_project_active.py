"""Tests for active project service operations."""

import pytest

from engram.models.project import Project
from engram.services.errors import EngramServiceError
from engram.services.project_service import (
    init_project,
    resolve_active_project,
    switch_project,
)


@pytest.fixture
def temp_active_file(tmp_path, monkeypatch):
    tmp_file = tmp_path / "active_project"
    monkeypatch.setattr("engram.services.project_service.ACTIVE_PROJECT_FILE_PATH", tmp_file)
    return tmp_file


def test_resolve_active_project_raises_no_active_project_initially(tmp_db, temp_active_file):
    with pytest.raises(EngramServiceError) as raised:
        resolve_active_project()
    assert raised.value.code == "NO_ACTIVE_PROJECT"


def test_resolve_active_project_raises_project_not_found_for_missing_db_project(
    tmp_db, temp_active_file
):
    temp_active_file.write_text("missing-project-id", encoding="utf-8")
    with pytest.raises(EngramServiceError) as raised:
        resolve_active_project()
    assert raised.value.code == "PROJECT_NOT_FOUND"


def test_init_project_creates_and_sets_active(tmp_db, temp_active_file):
    import os

    repo_path = os.path.abspath("/tmp/repo1")
    # Test project creation
    proj = init_project(
        id="proj-active-1",
        name="Active Project One",
        summary="A test active project",
        repo_paths=[repo_path],
    )
    assert proj["id"] == "proj-active-1"
    assert proj["name"] == "Active Project One"

    # Verify that file has been written
    assert temp_active_file.read_text(encoding="utf-8").strip() == "proj-active-1"

    # Verify we can resolve it
    resolved = resolve_active_project()
    assert resolved["id"] == "proj-active-1"
    assert resolved["name"] == "Active Project One"
    assert resolved["repo_paths"] == [repo_path]


def test_init_project_binds_existing(tmp_db, temp_active_file):
    import os

    repo2 = os.path.abspath("/tmp/repo2")
    repo3 = os.path.abspath("/tmp/repo3")
    # Pre-create the project
    Project.create("proj-active-2", "Existing Active Proj", repo_paths=[repo2])

    # Init project with same ID and a new repo path
    proj = init_project(
        id="proj-active-2",
        name="Existing Active Proj",
        repo_paths=[repo3],
    )
    assert proj["id"] == "proj-active-2"

    # Verify it bound both paths
    refreshed = Project.get("proj-active-2")
    assert repo2 in refreshed.repo_paths
    assert repo3 in refreshed.repo_paths

    # Verify active setting
    assert temp_active_file.read_text(encoding="utf-8").strip() == "proj-active-2"


def test_switch_project_success(tmp_db, temp_active_file):
    Project.create("proj-a", "Project A")
    Project.create("proj-b", "Project B")

    # Initial init to A
    init_project(id="proj-a", name="Project A")
    assert resolve_active_project()["id"] == "proj-a"

    # Switch to B
    proj_b = switch_project("proj-b")
    assert proj_b["id"] == "proj-b"
    assert temp_active_file.read_text(encoding="utf-8").strip() == "proj-b"
    assert resolve_active_project()["id"] == "proj-b"


def test_switch_project_raises_project_not_found_for_missing_id(tmp_db, temp_active_file):
    with pytest.raises(EngramServiceError) as raised:
        switch_project("nonexistent-switch")
    assert raised.value.code == "PROJECT_NOT_FOUND"
