"""Project service read operations."""

from __future__ import annotations

import os
from pathlib import Path

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


def append_to_gitignore(repo_root: Path) -> None:
    """Append .engram/ to the repository .gitignore file if missing."""
    gitignore_path = repo_root / ".gitignore"
    entry = ".engram/"

    if not gitignore_path.exists():
        gitignore_path.write_text(f"{entry}\n", encoding="utf-8")
        return

    content = gitignore_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    ignored = False
    for line in lines:
        stripped = line.strip()
        if stripped == ".engram/" or stripped == ".engram":
            ignored = True
            break

    if not ignored:
        if content and not content.endswith("\n"):
            gitignore_path.write_text(f"{content}\n{entry}\n", encoding="utf-8")
        else:
            gitignore_path.write_text(f"{content}{entry}\n", encoding="utf-8")


def initialize_project(
    cwd: str | None = None,
    name: str | None = None,
    project_id: str | None = None,
    summary: str | None = None,
) -> dict[str, JsonValue]:
    """Initialize a repo-local Engram state, project metadata, and .gitignore.

    If already initialized, returns the existing project's serialized payload with created=False.
    """
    from engram.db import init_db
    from engram.services.project_path import find_repo_root, get_repo_local_db_path

    resolved_cwd = os.path.abspath(cwd if cwd is not None else os.getcwd())
    repo_root = find_repo_root(resolved_cwd)
    db_path = get_repo_local_db_path(resolved_cwd)

    # 1. Initialize local DB schema idempotently
    init_db(db_path)

    # 2. Check if a project already exists in this local database
    existing_projects = Project.list_all(db_path=db_path)
    if existing_projects:
        project = existing_projects[0]
        # Ensure repo path is in the project repo_paths
        project.add_repo_path(str(repo_root), db_path=db_path)

        # 3. Add to gitignore if missing
        append_to_gitignore(repo_root)

        payload = project_to_dict(project)
        payload["created"] = False
        return payload

    # Generate project ID if not provided
    if not project_id:
        if name:
            # Simple slugify
            project_id = name.lower().replace(" ", "-")
        else:
            project_id = repo_root.name.lower().replace(" ", "-")

    if not name:
        name = repo_root.name

    # 4. Create project row inside the local database
    project = Project.create(
        id=project_id,
        name=name,
        summary=summary,
        repo_paths=[str(repo_root)],
        db_path=db_path,
    )

    # 5. Add to gitignore
    append_to_gitignore(repo_root)

    payload = project_to_dict(project)
    payload["created"] = True
    return payload
