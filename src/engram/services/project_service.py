"""Project service read operations."""

from __future__ import annotations

import os

from engram.models.project import Project
from engram.services.errors import EngramServiceError, JsonValue
from engram.services.serializers import project_to_dict


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
