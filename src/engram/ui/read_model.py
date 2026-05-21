"""Read-only query helpers for the local inspection UI."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from engram.db import get_db_connection


def _rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _row(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    rows = _rows(sql, params)
    return rows[0] if rows else None


def _split_tags(value: str | None) -> list[str]:
    return [tag for tag in (value or "").split(",") if tag]


def _with_tags(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    row["tag_list"] = _split_tags(row.get("tags"))
    _ensure_updated_at(row)
    return row


def _ensure_updated_at(row: dict[str, Any]) -> None:
    row.setdefault(
        "updated_at",
        row.get("created_at") or row.get("started_at") or row.get("closed_at") or "",
    )


def _table_columns(table: str) -> set[str]:
    conn = get_db_connection()
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    conn.close()
    return {row["name"] for row in rows}


def _timestamp_expr(table: str, fallback: str) -> str:
    columns = _table_columns(table)
    if "updated_at" in columns:
        return "updated_at"
    if fallback in columns:
        return fallback
    return "NULL"


def get_project(project_id: str) -> dict[str, Any] | None:
    """Return the current project row."""
    project = _row("SELECT * FROM projects WHERE id = ?", (project_id,))
    if project:
        _ensure_updated_at(project)
    return project


def list_tasks(
    project_id: str, status: str | None = None, query: str | None = None
) -> list[dict[str, Any]]:
    """Return tasks for a project with optional status and text filters."""
    sql = "SELECT * FROM tasks WHERE project_id = ?"
    params: list[Any] = [project_id]
    if status:
        sql += " AND status = ?"
        params.append(status)
    if query:
        sql += " AND (title LIKE ? OR description LIKE ? OR acceptance LIKE ? OR evidence LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like, like, like])
    sql += f"""
        ORDER BY
            CASE status
                WHEN 'in-progress' THEN 0
                WHEN 'blocked' THEN 1
                WHEN 'todo' THEN 2
                WHEN 'done' THEN 3
                ELSE 4
            END,
            CASE priority
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            {_timestamp_expr("tasks", "created_at")} DESC
    """
    return [_with_tags(row) for row in _rows(sql, tuple(params))]


def get_task(project_id: str, task_id: str) -> dict[str, Any] | None:
    """Return a single task in the current project."""
    return _with_tags(
        _row("SELECT * FROM tasks WHERE project_id = ? AND id = ?", (project_id, task_id))
    )


def count_tasks_by_status(project_id: str) -> dict[str, int]:
    """Return task counts by status."""
    rows = _rows(
        "SELECT status, COUNT(*) AS count FROM tasks WHERE project_id = ? GROUP BY status",
        (project_id,),
    )
    counts = {row["status"]: row["count"] for row in rows}
    for status in ("todo", "in-progress", "blocked", "done", "cancelled"):
        counts.setdefault(status, 0)
    return counts


def list_memories(
    project_id: str, memory_type: str | None = None, query: str | None = None
) -> list[dict[str, Any]]:
    """Return memories for a project with optional type and text filters."""
    sql = "SELECT * FROM memories WHERE project_id = ?"
    params: list[Any] = [project_id]
    if memory_type:
        sql += " AND type = ?"
        params.append(memory_type)
    if query:
        sql += " AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like, like])
    sql += f"""
        ORDER BY
            CASE type
                WHEN 'constraint' THEN 0
                WHEN 'lesson' THEN 1
                WHEN 'decision' THEN 2
                WHEN 'snippet' THEN 3
                ELSE 4
            END,
            {_timestamp_expr("memories", "created_at")} DESC
    """
    return [_with_tags(row) for row in _rows(sql, tuple(params))]


def get_memory(project_id: str, memory_id: str) -> dict[str, Any] | None:
    """Return a single memory in the current project."""
    return _with_tags(
        _row("SELECT * FROM memories WHERE project_id = ? AND id = ?", (project_id, memory_id))
    )


def group_memories_by_type(memories: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group memory rows by type for template rendering."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for memory in memories:
        grouped[memory["type"]].append(memory)
    return dict(grouped)


def list_audit_events(project_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Return recent audit events associated with project-owned rows."""
    target_ids = _project_target_ids(project_id)
    if not target_ids:
        return []
    placeholders = ",".join("?" for _ in target_ids)
    return _rows(
        f"""
        SELECT * FROM audit_log
        WHERE target_id IN ({placeholders})
        ORDER BY timestamp DESC, id DESC
        LIMIT ?
        """,
        (*target_ids, limit),
    )


def get_dashboard(project_id: str) -> dict[str, Any]:
    """Return the dense dashboard snapshot for the current project."""
    tasks = list_tasks(project_id)
    memories = list_memories(project_id)
    return {
        "project": get_project(project_id),
        "task_counts": count_tasks_by_status(project_id),
        "active_tasks": [task for task in tasks if task["status"] in ("todo", "in-progress")][:8],
        "blocked_tasks": [task for task in tasks if task["status"] == "blocked"][:8],
        "recent_memories": memories[:8],
        "memory_counts": dict(Counter(memory["type"] for memory in memories)),
        "recent_audit": list_audit_events(project_id, limit=10),
        "snapshot_version": get_snapshot_version(project_id),
    }


def get_snapshot_version(project_id: str) -> str:
    """Return a stable version token for the latest project DB change."""
    target_ids = _project_target_ids(project_id)
    audit_max = None
    if target_ids:
        placeholders = ",".join("?" for _ in target_ids)
        row = _row(
            f"SELECT MAX(timestamp) AS latest FROM audit_log WHERE target_id IN ({placeholders})",
            tuple(target_ids),
        )
        audit_max = row["latest"] if row else None

    row = _row(
        """
        SELECT MAX(latest) AS latest FROM (
            SELECT {project_ts} AS latest FROM projects WHERE id = ?
            UNION ALL
            SELECT {task_ts} AS latest FROM tasks WHERE project_id = ?
            UNION ALL
            SELECT {memory_ts} AS latest FROM memories WHERE project_id = ?
        )
        """.format(
            project_ts=_timestamp_expr("projects", "created_at"),
            task_ts=_timestamp_expr("tasks", "created_at"),
            memory_ts=_timestamp_expr("memories", "created_at"),
        ),
        (project_id, project_id, project_id),
    )
    row_max = row["latest"] if row else None
    return max(value for value in (row_max, audit_max, "0") if value is not None)


def _project_target_ids(project_id: str) -> tuple[str, ...]:
    rows = _rows(
        """
        SELECT id FROM projects WHERE id = ?
        UNION ALL
        SELECT id FROM tasks WHERE project_id = ?
        UNION ALL
        SELECT id FROM memories WHERE project_id = ?
        """,
        (project_id, project_id, project_id),
    )
    return tuple(row["id"] for row in rows)
