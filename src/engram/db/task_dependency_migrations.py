"""Task dependency migration helpers."""

from __future__ import annotations

import sqlite3


def _normalize_text(value: str | None) -> str:
    """Normalize whitespace and casing for legacy reference matching."""
    if value is None:
        return ""
    return " ".join(value.split()).casefold()


def _collect_ids_by_title(project_rows: list[sqlite3.Row]) -> dict[str, set[str]]:
    """Build normalized title -> task IDs mapping."""
    mapped: dict[str, set[str]] = {}
    for row in project_rows:
        normalized = _normalize_text(str(row["title"]))
        if normalized:
            mapped.setdefault(normalized, set()).add(str(row["id"]))
    return mapped


def _collect_ids_by_title_token(project_rows: list[sqlite3.Row]) -> dict[str, set[str]]:
    """Build first title token -> task IDs mapping."""
    mapped: dict[str, set[str]] = {}
    for row in project_rows:
        title = " ".join(str(row["title"]).split())
        if not title:
            continue
        token = title.split(" ", 1)[0]
        mapped.setdefault(token, set()).add(str(row["id"]))
    return mapped


def _resolve_legacy_dependency_ref(
    *,
    dep_ref: str,
    id_set: set[str],
    ids_by_title: dict[str, set[str]],
    ids_by_title_token: dict[str, set[str]],
) -> str | None:
    """Resolve a legacy dependency reference to a single task ID."""
    if dep_ref in id_set:
        return dep_ref

    prefix_matches = sorted(task_id for task_id in id_set if task_id.startswith(dep_ref))
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    if len(prefix_matches) > 1:
        return None

    token_matches = sorted(ids_by_title_token.get(dep_ref, set()))
    if len(token_matches) == 1:
        return token_matches[0]
    if len(token_matches) > 1:
        return None

    title_matches = sorted(ids_by_title.get(_normalize_text(dep_ref), set()))
    if len(title_matches) == 1:
        return title_matches[0]
    return None


def apply_task_dependency_ref_migrations(cursor: sqlite3.Cursor) -> None:
    """Normalize legacy task dependency references to canonical task IDs."""
    dep_rows = cursor.execute(
        """
        SELECT id, project_id, title, depends_on
        FROM tasks
        WHERE depends_on IS NOT NULL AND TRIM(depends_on) != ''
        """
    ).fetchall()
    if not dep_rows:
        return

    project_ids = sorted({str(row["project_id"]) for row in dep_rows})
    placeholders = ",".join("?" for _ in project_ids)
    all_rows = cursor.execute(
        f"""
        SELECT id, project_id, title
        FROM tasks
        WHERE project_id IN ({placeholders})
        """,
        project_ids,
    ).fetchall()

    all_rows_by_project: dict[str, list[sqlite3.Row]] = {}
    for row in all_rows:
        all_rows_by_project.setdefault(str(row["project_id"]), []).append(row)
    dep_rows_by_project: dict[str, list[sqlite3.Row]] = {}
    for row in dep_rows:
        dep_rows_by_project.setdefault(str(row["project_id"]), []).append(row)

    for project_id, project_rows in all_rows_by_project.items():
        id_set = {str(row["id"]) for row in project_rows}
        ids_by_title = _collect_ids_by_title(project_rows)
        ids_by_title_token = _collect_ids_by_title_token(project_rows)

        for row in dep_rows_by_project.get(project_id, []):
            dep_ref = str(row["depends_on"]).strip()
            task_id = str(row["id"])
            resolved = _resolve_legacy_dependency_ref(
                dep_ref=dep_ref,
                id_set=id_set,
                ids_by_title=ids_by_title,
                ids_by_title_token=ids_by_title_token,
            )
            if resolved and resolved != dep_ref and resolved != task_id:
                cursor.execute(
                    "UPDATE tasks SET depends_on = ? WHERE id = ?",
                    (resolved, task_id),
                )
