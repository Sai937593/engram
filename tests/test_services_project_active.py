"""Tests for active project service operations."""

from __future__ import annotations

import os

import pytest

from engram.models.project import Project
from engram.services.errors import EngramServiceError
from engram.services.project_service import (
    init_project,
    resolve_active_project,
    switch_project,
)


@pytest.fixture(autouse=True)
def setup_active_file(tmp_path, monkeypatch):
    """Isolate active project configuration file for each test."""
    active_file = tmp_path / "active_project"
    monkeypatch.setattr("engram.services.project_service.ACTIVE_PROJECT_FILE", active_file)
    return active_file


def test_resolve_active_project_auto_activates_if_single_project(tmp_db):
    """Verify resolve_active_project auto-activates if there is exactly one project."""
    Project.create(
        id="proj-single",
        name="Single Project",
        summary="Only one project",
        repo_paths=["/path/to/single"],
    )

    # Should not raise an error, but instead auto-activate and return it
    payload = resolve_active_project()
    assert payload["id"] == "proj-single"
    assert payload["name"] == "Single Project"


def test_resolve_active_project_raises_not_bound_if_no_project_and_multiple_or_none(tmp_db):
    """Verify resolve_active_project raises PROJECT_NOT_BOUND if no project is set and multiple or zero exist."""
    # Zero projects case
    with pytest.raises(EngramServiceError) as raised:
        resolve_active_project()
    assert raised.value.code == "PROJECT_NOT_BOUND"

    # Multiple projects case
    Project.create(id="proj1", name="Project 1")
    Project.create(id="proj2", name="Project 2")

    with pytest.raises(EngramServiceError) as raised:
        resolve_active_project()
    assert raised.value.code == "PROJECT_NOT_BOUND"


def test_resolve_active_project_resolves_when_configured(tmp_db):
    """Verify resolve_active_project resolves correctly when active project is configured."""
    Project.create(id="proj1", name="Project 1")
    Project.create(id="proj2", name="Project 2")

    switch_project("proj2")

    payload = resolve_active_project()
    assert payload["id"] == "proj2"
    assert payload["name"] == "Project 2"


def test_init_project_success(tmp_db, tmp_path):
    """Verify init_project successfully creates a project and makes it active."""
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir()

    payload = init_project(
        id="new-proj",
        name="New Project",
        summary="A brand new project",
        repo_path=str(repo_dir),
    )

    assert payload["id"] == "new-proj"
    assert payload["name"] == "New Project"
    assert payload["summary"] == "A brand new project"
    assert payload["repo_paths"] == [os.path.abspath(repo_dir)]

    # Check active state
    active = resolve_active_project()
    assert active["id"] == "new-proj"


def test_init_project_validations(tmp_db):
    """Verify init_project raises error for invalid inputs or existing IDs."""
    with pytest.raises(EngramServiceError) as raised:
        init_project(id="", name="Valid Name")
    assert raised.value.code == "INVALID_PROJECT_ID"

    with pytest.raises(EngramServiceError) as raised:
        init_project(id="valid-id", name=" ")
    assert raised.value.code == "INVALID_PROJECT_NAME"

    Project.create(id="existing", name="Existing")
    with pytest.raises(EngramServiceError) as raised:
        init_project(id="existing", name="Duplicate")
    assert raised.value.code == "PROJECT_ALREADY_EXISTS"


def test_switch_project_validations(tmp_db):
    """Verify switch_project raises error for non-existent projects."""
    with pytest.raises(EngramServiceError) as raised:
        switch_project("non-existent")
    assert raised.value.code == "PROJECT_NOT_FOUND"
