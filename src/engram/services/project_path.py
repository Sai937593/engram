"""Services for project path and workspace resolution."""

from __future__ import annotations

import os
from pathlib import Path

from engram.services.errors import EngramServiceError


def find_repo_root(cwd: str | None = None) -> Path:
    """Find the Git repository or workspace root containing the given cwd.

    Climbs up the directory tree looking for a `.git` directory.
    If no `.git` is found, raises EngramServiceError(code="UNRESOLVED_WORKSPACE", ...).
    """
    resolved_cwd = Path(os.path.abspath(cwd if cwd is not None else os.getcwd()))

    current = resolved_cwd
    while True:
        git_dir = current / ".git"
        if git_dir.is_dir():
            return current
        parent = current.parent
        if parent == current:  # Reached system root
            raise EngramServiceError(
                code="UNRESOLVED_WORKSPACE",
                message="Could not resolve repository root from the current path.",
                details={"cwd": str(resolved_cwd)},
            )
        current = parent


def get_repo_local_engram_dir(cwd: str | None = None) -> Path:
    """Return the path to the repo-local .engram directory."""
    root = find_repo_root(cwd)
    return root / ".engram"


def get_repo_local_db_path(cwd: str | None = None) -> Path:
    """Return the path to the repo-local SQLite database file."""
    engram_dir = get_repo_local_engram_dir(cwd)
    return engram_dir / "memory.db"
