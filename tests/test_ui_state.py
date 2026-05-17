"""Tests for UI runtime project resolution state."""

import pytest

from engram.models.project import Project
from engram.ui import state as ui_state


def test_resolve_target_from_registered_repo(project, tmp_path, monkeypatch):
    """UI state resolves from the current registered repository."""
    repo = tmp_path / "repo"
    repo.mkdir()
    project.add_repo_path(str(repo))
    monkeypatch.setattr(ui_state, "_git_root", lambda path: None)

    target = ui_state.resolve_target_from_cwd(repo)

    assert target.project_id == project.id
    assert target.repo_path == str(repo)


def test_resolve_target_prefers_git_root(project, tmp_path, monkeypatch):
    """Running from a subdirectory resolves the containing Git root."""
    repo = tmp_path / "repo"
    subdir = repo / "src" / "pkg"
    subdir.mkdir(parents=True)
    project.add_repo_path(str(repo))
    monkeypatch.setattr(ui_state, "_git_root", lambda path: repo)

    target = ui_state.resolve_target_from_cwd(subdir)

    assert target.project_id == project.id
    assert target.repo_path == str(repo)


def test_unregistered_cwd_fails_clearly(tmp_db, tmp_path, monkeypatch):
    """Unregistered directories do not fall back to the Engram repo."""
    monkeypatch.setattr(ui_state, "_git_root", lambda path: None)

    with pytest.raises(ui_state.UiStateError, match="engram init"):
        ui_state.resolve_target_from_cwd(tmp_path)


def test_duplicate_repo_binding_fails_clearly(tmp_db, tmp_path, monkeypatch):
    """Ambiguous duplicate repo bindings fail instead of selecting the first row."""
    repo = tmp_path / "repo"
    repo.mkdir()
    Project.create("proj-a", "Project A", repo_paths=[str(repo)])
    Project.create("proj-b", "Project B", repo_paths=[str(repo)])
    monkeypatch.setattr(ui_state, "_git_root", lambda path: None)

    with pytest.raises(ui_state.UiStateError, match="proj-a, proj-b"):
        ui_state.resolve_target_from_cwd(repo)


def test_write_and_read_target_round_trip(tmp_path):
    """Persisted UI state round-trips through JSON."""
    target = ui_state.UiTarget(
        project_id="proj",
        project_name="Project",
        repo_path=str(tmp_path),
        version="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    state_path = tmp_path / "ui_state.json"

    ui_state.write_target(target, state_path)

    assert ui_state.read_target(state_path) == target
