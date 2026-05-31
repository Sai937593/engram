"""Project status inspection service for MCP current-project surfaces."""

from __future__ import annotations

import os

from engram.services.errors import EngramServiceError, JsonValue
from engram.services.project_path import find_repo_root, get_repo_local_db_path
from engram.services.project_service import resolve_current_project


def get_current_project_status(cwd: str | None = None) -> dict[str, JsonValue]:
    """Return compact repo-local Engram status for the current workspace."""
    resolved_cwd = os.path.abspath(cwd if cwd is not None else os.getcwd())
    try:
        repo_root = find_repo_root(resolved_cwd)
    except EngramServiceError as exc:
        if exc.code != "UNRESOLVED_WORKSPACE":
            raise
        return {
            "initialized": False,
            "workspace": resolved_cwd,
            "status": "unresolved-workspace",
            "next_action": "Run git init in this workspace, then run engram_project_init.",
        }

    db_path = get_repo_local_db_path(resolved_cwd)
    try:
        project = resolve_current_project(cwd=resolved_cwd)
    except EngramServiceError as exc:
        if exc.code != "PROJECT_NOT_BOUND":
            raise
        return _uninitialized_status(resolved_cwd, repo_root=str(repo_root), db_path=str(db_path))
    except Exception:
        return _uninitialized_status(resolved_cwd, repo_root=str(repo_root), db_path=str(db_path))

    return {
        "initialized": True,
        "workspace": resolved_cwd,
        "repo_root": str(repo_root),
        "db_path": str(db_path),
        "db_exists": db_path.exists(),
        "status": "ready",
        "project": project,
    }


def _uninitialized_status(
    workspace: str,
    *,
    repo_root: str,
    db_path: str,
) -> dict[str, JsonValue]:
    """Build a compact uninitialized-status payload."""
    return {
        "initialized": False,
        "workspace": workspace,
        "repo_root": repo_root,
        "db_path": db_path,
        "db_exists": os.path.exists(db_path),
        "status": "uninitialized",
        "next_action": "Run engram_project_init in this repository.",
    }
