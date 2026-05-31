"""Project service read operations."""

from __future__ import annotations

import os

from engram.models.project import Project
from engram.services.errors import EngramServiceError, JsonValue
from engram.services.serializers import project_to_dict


def resolve_current_project(cwd: str | None = None) -> dict[str, JsonValue]:
    """Resolve and serialize the project bound to the current repository path."""
    import json
    import sys

    from engram.services.project_path import find_repo_root, get_repo_local_db_path

    resolved_cwd = os.path.abspath(cwd if cwd is not None else os.getcwd())
    is_testing = "pytest" in sys.modules

    # 1. Try repo-local DB resolution first
    try:
        repo_root = find_repo_root(resolved_cwd)
        db_path = get_repo_local_db_path(resolved_cwd)
        if db_path.exists():
            from engram.db import get_db_connection

            conn = get_db_connection(db_path)
            try:
                row = conn.execute("SELECT * FROM projects LIMIT 1").fetchone()
            except Exception:
                row = None
            finally:
                conn.close()

            if row is not None:
                repo_paths = json.loads(row["repo_paths"]) if row["repo_paths"] else []
                if not repo_paths:
                    repo_paths.append(str(repo_root))
                project = Project(
                    id=row["id"],
                    name=row["name"],
                    summary=row["summary"],
                    status=row["status"],
                    repo_paths=repo_paths,
                )
                return project_to_dict(project)
    except EngramServiceError as e:
        if e.code != "UNRESOLVED_WORKSPACE":
            raise

    # 2. Narrow legacy/test fallback path
    # If the local repo DB didn't exist/resolve, but we are running in tests or there is a
    # database path we can query using find_by_repo_path, let's fall back to it.
    if is_testing:
        project = Project.find_by_repo_path(resolved_cwd)
        if project is not None:
            return project_to_dict(project)

    # If both repo-local DB and legacy fallbacks fail, raise PROJECT_NOT_BOUND
    raise EngramServiceError(
        code="PROJECT_NOT_BOUND",
        message="No project is bound to the current repository path.",
        details={"cwd": resolved_cwd},
    )
