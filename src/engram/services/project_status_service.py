"""Project status inspection service for MCP current-project surfaces."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

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


def get_project_diagnostics(cwd: str | None = None) -> dict[str, JsonValue]:
    """Return diagnostics for workspace binding, DB/schema health, and .gitignore state."""
    resolved_cwd = os.path.abspath(cwd if cwd is not None else os.getcwd())
    try:
        repo_root = find_repo_root(resolved_cwd)
    except EngramServiceError as exc:
        if exc.code != "UNRESOLVED_WORKSPACE":
            raise
        return {
            "workspace": resolved_cwd,
            "status": "unresolved-workspace",
            "repo_root_detected": False,
            "next_action": "Run git init in this workspace, then run engram_project_init.",
        }

    db_path = get_repo_local_db_path(resolved_cwd)
    db_health = _inspect_db_health(db_path)
    gitignore = _inspect_gitignore(repo_root)

    status = "healthy"
    if not db_path.exists():
        status = "uninitialized"
    elif db_health["status"] != "healthy" or gitignore["status"] != "configured":
        status = "misconfigured"

    return {
        "workspace": resolved_cwd,
        "repo_root_detected": True,
        "repo_root": str(repo_root),
        "status": status,
        "db": db_health,
        "gitignore": gitignore,
        "next_action": _diagnostic_next_action(status, db_health, gitignore),
    }


def _inspect_db_health(db_path: Path) -> dict[str, JsonValue]:
    """Inspect local DB file and essential schema availability."""
    payload: dict[str, JsonValue] = {
        "path": str(db_path),
        "exists": db_path.exists(),
        "status": "missing",
        "schema_ok": False,
    }
    if not db_path.exists():
        return payload

    conn = None
    try:
        from engram.db import get_db_connection

        conn = get_db_connection(db_path)
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        integrity_val = str(integrity[0]) if integrity else "failed"
        schema_rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('projects', 'tasks', 'phases', 'memories')"
        ).fetchall()
        table_names = sorted(row[0] for row in schema_rows)
        schema_ok = len(table_names) == 4
        payload.update(
            {
                "integrity_check": integrity_val,
                "tables_present": table_names,
                "schema_ok": schema_ok,
                "status": "healthy" if integrity_val == "ok" and schema_ok else "schema-invalid",
            }
        )
        return payload
    except (sqlite3.DatabaseError, OSError, ValueError):
        payload["status"] = "unreadable"
        return payload
    finally:
        if conn is not None:
            conn.close()


def _inspect_gitignore(repo_root: Path) -> dict[str, JsonValue]:
    """Inspect whether .engram/ is present in .gitignore."""
    gitignore_path = repo_root / ".gitignore"
    payload: dict[str, JsonValue] = {
        "path": str(gitignore_path),
        "exists": gitignore_path.exists(),
        "has_engram_entry": False,
        "status": "missing-file",
    }
    if not gitignore_path.exists():
        return payload

    content = gitignore_path.read_text(encoding="utf-8")
    has_entry = any(line.strip() in {".engram", ".engram/"} for line in content.splitlines())
    payload["has_engram_entry"] = has_entry
    payload["status"] = "configured" if has_entry else "missing-entry"
    return payload


def _diagnostic_next_action(
    status: str,
    db_health: dict[str, JsonValue],
    gitignore: dict[str, JsonValue],
) -> str | None:
    """Return a single actionable next step for diagnostics consumers."""
    if status == "healthy":
        return None
    if status == "uninitialized":
        return "Run engram_project_init in this repository."
    if db_health.get("status") in {"schema-invalid", "unreadable"}:
        return "Run engram_project_init to repair or recreate the repo-local Engram DB."
    if gitignore.get("status") != "configured":
        return "Run engram_project_init to ensure .engram/ is configured in .gitignore."
    return "Run engram_project_init in this repository."
