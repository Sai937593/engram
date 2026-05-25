"""Tests for project service read boundaries."""

from __future__ import annotations

import os

import pytest

import engram.services.project_service as project_service
from engram.models.project import Project
from engram.services.errors import EngramServiceError
from engram.services.project_service import resolve_current_project


def test_resolve_current_project_returns_serialized_project_for_bound_repo(tmp_db):
    repo_path = os.path.abspath("repo/bound")
    Project.create(
        id="proj1234",
        name="Bound Project",
        summary="Service test project",
        repo_paths=[repo_path],
    )

    payload = resolve_current_project(cwd=repo_path)

    assert payload == {
        "id": "proj1234",
        "name": "Bound Project",
        "summary": "Service test project",
        "status": "active",
        "repo_paths": [repo_path],
    }


def test_resolve_current_project_raises_project_not_bound_for_unbound_repo(tmp_db):
    cwd = os.path.abspath("repo/unbound")

    with pytest.raises(EngramServiceError) as raised:
        resolve_current_project(cwd=cwd)
    error = raised.value
    assert error.code == "PROJECT_NOT_BOUND"
    assert error.message == "No project is bound to the current repository path."
    assert error.details == {"cwd": cwd}


def test_resolve_current_project_uses_os_getcwd_when_cwd_is_omitted(monkeypatch):
    captured: dict[str, str] = {}
    raw_cwd = "./repo/default-cwd"

    monkeypatch.setattr(project_service.os, "getcwd", lambda: raw_cwd)

    expected = Project(
        id="proj-default",
        name="Default Cwd Project",
        summary=None,
        status="active",
        repo_paths=[os.path.abspath(raw_cwd)],
    )

    def _find_by_repo_path(cls, path: str) -> Project:
        captured["path"] = path
        return expected

    monkeypatch.setattr(
        project_service.Project,
        "find_by_repo_path",
        classmethod(_find_by_repo_path),
    )

    payload = resolve_current_project()

    assert captured["path"] == os.path.abspath(raw_cwd)
    assert payload["id"] == "proj-default"
    assert payload["name"] == "Default Cwd Project"
    assert payload["status"] == "active"
    assert payload["repo_paths"] == [os.path.abspath(raw_cwd)]
