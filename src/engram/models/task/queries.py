from typing import Any

from engram.db import get_db_connection
from engram.models.task.model import Task

PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class _TaskQueryHelper:
    @staticmethod
    def normalize_phase_title(phase: str | None) -> str:
        """Return a whitespace-normalized phase key for compatibility matching."""
        if phase is None:
            return ""
        return " ".join(phase.split()).casefold()

    @staticmethod
    def list_actionable_todo_rows(project_id: str) -> list[Any]:
        """Return todo task rows whose dependencies are satisfied."""
        conn = get_db_connection()
        rows = conn.execute(
            """
            SELECT t1.*, t2.status AS dependency_status
            FROM tasks t1
            LEFT JOIN tasks t2 ON t1.depends_on = t2.id
            WHERE t1.project_id = ?
              AND t1.status = 'todo'
              AND (t1.depends_on IS NULL OR t2.status = 'done')
            """,
            (project_id,),
        ).fetchall()
        conn.close()
        return rows

    @staticmethod
    def select_next_from_rows(rows: list[Any]) -> Task | None:
        """Select the highest-priority row using the same ordering as get_next."""
        if not rows:
            return None

        ordered_rows = sorted(
            rows,
            key=lambda row: (
                PRIORITY_RANK.get(row["priority"], 4),
                row["created_at"] or "",
            ),
        )
        return Task.from_row(ordered_rows[0])


def list_by_project(project_id: str) -> list[Task]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM tasks WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()
    return [Task.from_row(row) for row in rows]


def get(id: str) -> Task | None:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (id,)).fetchone()
    conn.close()
    if row:
        return Task.from_row(row)
    return None


def get_next(project_id: str, active_phase_id: str | None = None) -> Task | None:
    """Return the highest-priority todo task, respecting dependencies."""
    priority_order = "CASE t1.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END"
    conn = get_db_connection()
    # Find a task that is 'todo', and either has no dependency, OR its dependency is 'done'
    if active_phase_id:
        query = f"""
            SELECT t1.* FROM tasks t1
            LEFT JOIN tasks t2 ON t1.depends_on = t2.id
            WHERE t1.project_id = ?
              AND t1.phase_id = ?
              AND t1.status = 'todo'
              AND (t1.depends_on IS NULL OR t2.status = 'done')
            ORDER BY {priority_order}, t1.created_at ASC
            LIMIT 1
        """
        row = conn.execute(query, (project_id, active_phase_id)).fetchone()
        if row:
            conn.close()
            return Task.from_row(row)

    query = f"""
        SELECT t1.* FROM tasks t1
        LEFT JOIN tasks t2 ON t1.depends_on = t2.id
        WHERE t1.project_id = ?
          AND t1.status = 'todo'
          AND (t1.depends_on IS NULL OR t2.status = 'done')
        ORDER BY {priority_order}, t1.created_at ASC
        LIMIT 1
    """
    row = conn.execute(query, (project_id,)).fetchone()
    conn.close()
    if row:
        return Task.from_row(row)
    return None


def get_next_for_phase(project_id: str, phase_id: str, phase_title: str) -> Task | None:
    """Return the next actionable task linked to a phase by phase_id or legacy title."""
    normalized_title = _TaskQueryHelper.normalize_phase_title(phase_title)
    rows = [
        row
        for row in _TaskQueryHelper.list_actionable_todo_rows(project_id)
        if row["phase_id"] == phase_id
        or (
            not row["phase_id"]
            and _TaskQueryHelper.normalize_phase_title(row["phase"]) == normalized_title
        )
    ]
    return _TaskQueryHelper.select_next_from_rows(rows)


def get_next_unphased(project_id: str) -> Task | None:
    """Return the next actionable task with no first-class or legacy phase."""
    rows = [
        row
        for row in _TaskQueryHelper.list_actionable_todo_rows(project_id)
        if not row["phase_id"] and not _TaskQueryHelper.normalize_phase_title(row["phase"])
    ]
    return _TaskQueryHelper.select_next_from_rows(rows)


def count_by_status(project_id: str) -> dict[str, int]:
    """Return a dict of status → count for all tasks in the project."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM tasks WHERE project_id = ? GROUP BY status",
        (project_id,),
    ).fetchall()
    conn.close()
    return {row["status"]: row["cnt"] for row in rows}


def get_effective_phase_title(task: Task) -> str | None:
    """Return the workflow/display phase title for a task across legacy and first-class phases."""
    if task.phase_id:
        from engram.models.phase import Phase

        phase = Phase.get(task.phase_id)
        if phase:
            return phase.title

    if isinstance(task.phase, str) and task.phase.strip():
        return task.phase

    return None
