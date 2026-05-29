"""Project service read operations."""

from __future__ import annotations

import os
from pathlib import Path

from engram.models.project import Project
from engram.services.errors import EngramServiceError, JsonValue
from engram.services.serializers import project_to_dict

ACTIVE_PROJECT_FILE_PATH = Path.home() / ".engram" / "active_project"


def get_active_project_file() -> Path:
    """Return the path to the active project tracking file."""
    return ACTIVE_PROJECT_FILE_PATH


def resolve_current_project(cwd: str | None = None) -> dict[str, JsonValue]:
    """Resolve and serialize the project bound to the current repository path."""
    resolved_cwd = os.path.abspath(cwd if cwd is not None else os.getcwd())
    project = Project.find_by_repo_path(resolved_cwd)
    if project is None:
        raise EngramServiceError(
            code="PROJECT_NOT_BOUND",
            message="No project is bound to the current repository path.",
            details={"cwd": resolved_cwd},
        )
    return project_to_dict(project)


def resolve_active_project() -> dict[str, JsonValue]:
    """Resolve and serialize the currently active project without CWD fallback."""
    active_project_file = get_active_project_file()
    project_id = None
    if active_project_file.exists():
        try:
            project_id = active_project_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    if not project_id:
        raise EngramServiceError(
            code="NO_ACTIVE_PROJECT",
            message="No active project is selected.",
            fix="Initialize or switch to a project using engram_project_init or engram_project_switch.",
        )

    project = Project.get(project_id)
    if project is None:
        raise EngramServiceError(
            code="PROJECT_NOT_FOUND",
            message=f"Active project with ID '{project_id}' was not found in the database.",
            fix="Initialize or switch to a valid project using engram_project_init or engram_project_switch.",
        )
    return project_to_dict(project)


def set_active_project(project_id: str) -> None:
    """Set the active project ID in the local config file."""
    active_project_file = get_active_project_file()
    try:
        active_project_file.parent.mkdir(parents=True, exist_ok=True)
        active_project_file.write_text(project_id, encoding="utf-8")
    except Exception as exc:
        raise EngramServiceError(
            code="ACTIVE_PROJECT_WRITE_FAILED",
            message=f"Failed to write active project file: {exc}",
        ) from exc


def init_project(
    id: str | None = None,
    name: str | None = None,
    summary: str | None = None,
    repo_paths: list[str] | None = None,
) -> dict[str, JsonValue]:
    """Initialize a new project (creating it if missing, or binding to it) and set it active."""
    if not name:
        raise EngramServiceError(
            code="INVALID_PROJECT_NAME",
            message="Project name is required for initialization.",
        )

    project_id = id
    if not project_id:
        project_id = name.lower().replace(" ", "-")

    project = Project.get(project_id)
    if project:
        # Binding current repo_paths to it if provided
        if repo_paths:
            for path in repo_paths:
                project.add_repo_path(path)
    else:
        # Create the project
        project = Project.create(project_id, name, summary, repo_paths=repo_paths)

    set_active_project(project_id)
    return project_to_dict(project)


def switch_project(id: str) -> dict[str, JsonValue]:
    """Switch the active project to the given ID."""
    project = Project.get(id)
    if project is None:
        raise EngramServiceError(
            code="PROJECT_NOT_FOUND",
            message=f"Project with ID '{id}' was not found.",
            fix="Create the project first using engram_project_init.",
        )
    set_active_project(id)
    return project_to_dict(project)
