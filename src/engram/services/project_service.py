"""Project service read and write operations."""

from __future__ import annotations

import os
from pathlib import Path

from engram.models.project import Project
from engram.services.errors import EngramServiceError, JsonValue
from engram.services.serializers import project_to_dict

DEFAULT_ACTIVE_PROJECT_FILE = Path.home() / ".engram" / "active_project"
ACTIVE_PROJECT_FILE = DEFAULT_ACTIVE_PROJECT_FILE


def get_active_project_id() -> str | None:
    """Return the currently configured active project ID, if set."""
    if ACTIVE_PROJECT_FILE.exists():
        try:
            return ACTIVE_PROJECT_FILE.read_text(encoding="utf-8").strip() or None
        except Exception:
            return None
    return None


def set_active_project_id(project_id: str) -> None:
    """Persist the active project ID to the configuration file."""
    try:
        ACTIVE_PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_PROJECT_FILE.write_text(project_id.strip(), encoding="utf-8")
    except Exception as exc:
        raise EngramServiceError(
            code="PROJECT_SAVE_FAILED",
            message=f"Failed to persist active project ID to {ACTIVE_PROJECT_FILE}.",
            details={"error": str(exc)},
        ) from exc


def resolve_current_project(cwd: str | None = None) -> dict[str, JsonValue]:
    """Resolve and serialize the project bound to the current repository path (for CLI)."""
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
    """Resolve the active project for MCP, failing if not set or non-existent.

    Has a safe fallback: if no active project ID is set, but there is exactly one
    project in the database, it auto-activates it and returns it.
    """
    project_id = get_active_project_id()

    if not project_id:
        # Check if there is exactly one project in the database
        all_projects = Project.list_all()
        if len(all_projects) == 1:
            single_project = all_projects[0]
            set_active_project_id(single_project.id)
            return project_to_dict(single_project)

        raise EngramServiceError(
            code="PROJECT_NOT_BOUND",
            message="No active project has been selected for the MCP session. Use engram_project_init or engram_project_switch to set an active project.",
        )

    project = Project.get(project_id)
    if project is None:
        # Check if there is exactly one project in the database as fallback
        all_projects = Project.list_all()
        if len(all_projects) == 1:
            single_project = all_projects[0]
            set_active_project_id(single_project.id)
            return project_to_dict(single_project)

        raise EngramServiceError(
            code="PROJECT_NOT_BOUND",
            message=f"The active project with ID '{project_id}' does not exist in the database.",
            details={"project_id": project_id},
        )

    return project_to_dict(project)


def init_project(
    id: str, name: str, summary: str | None = None, repo_path: str | None = None
) -> dict[str, JsonValue]:
    """Create a new project, bind it to a repository path, and set it as active."""
    cleaned_id = id.strip()
    cleaned_name = name.strip()

    if not cleaned_id:
        raise EngramServiceError(code="INVALID_PROJECT_ID", message="Project ID cannot be empty.")
    if not cleaned_name:
        raise EngramServiceError(
            code="INVALID_PROJECT_NAME", message="Project name cannot be empty."
        )

    existing = Project.get(cleaned_id)
    if existing is not None:
        raise EngramServiceError(
            code="PROJECT_ALREADY_EXISTS",
            message=f"Project with ID '{cleaned_id}' already exists.",
            details={"project_id": cleaned_id},
        )

    resolved_paths = []
    if repo_path:
        resolved_paths.append(os.path.abspath(repo_path))
    else:
        resolved_paths.append(os.path.abspath(os.getcwd()))

    project = Project.create(
        id=cleaned_id, name=cleaned_name, summary=summary, repo_paths=resolved_paths
    )
    set_active_project_id(cleaned_id)
    return project_to_dict(project)


def switch_project(project_id: str) -> dict[str, JsonValue]:
    """Switch the currently active project to the specified ID."""
    cleaned_id = project_id.strip()
    project = Project.get(cleaned_id)
    if project is None:
        raise EngramServiceError(
            code="PROJECT_NOT_FOUND",
            message=f"Project with ID '{cleaned_id}' does not exist.",
            details={"project_id": cleaned_id},
        )
    set_active_project_id(cleaned_id)
    return project_to_dict(project)
