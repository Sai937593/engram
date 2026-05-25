import json
import uuid
from typing import Any

from engram.db import get_db_connection
from engram.models.audit import AuditLog

PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _normalize_phase_title(phase: str | None) -> str:
    """Return a whitespace-normalized phase key for compatibility matching."""
    if phase is None:
        return ""
    return " ".join(phase.split()).casefold()


def _normalize_relevant_files(relevant_files: Any) -> list[str]:
    """Normalize relevant file paths by trimming entries and dropping empties."""
    if relevant_files is None:
        return []
    if isinstance(relevant_files, str):
        candidates = [relevant_files]
    else:
        candidates = list(relevant_files)

    normalized: list[str] = []
    for path in candidates:
        if path is None:
            continue
        cleaned = str(path).strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def _serialize_relevant_files(relevant_files: list[str]) -> str:
    """Serialize relevant files for database storage."""
    return json.dumps(relevant_files)


def _deserialize_relevant_files(value: Any) -> list[str]:
    """Deserialize relevant file path metadata from DB values."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return _normalize_relevant_files(value.split(","))
        return _normalize_relevant_files(loaded)
    return _normalize_relevant_files(value)


class Task:
    def __init__(
        self,
        id,
        project_id,
        title,
        description=None,
        status="todo",
        priority="medium",
        phase=None,
        phase_id=None,
        depends_on=None,
        acceptance=None,
        evidence=None,
        tags=None,
        relevant_files=None,
    ):
        self.id = id
        self.project_id = project_id
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.phase = phase
        self.phase_id = phase_id
        self.depends_on = depends_on
        self.acceptance = acceptance
        self.evidence = evidence
        self.tags = tags or []
        self.relevant_files = _normalize_relevant_files(relevant_files)

    @classmethod
    def create(
        cls,
        project_id,
        title,
        description=None,
        status="todo",
        priority="medium",
        phase=None,
        phase_id=None,
        depends_on=None,
        acceptance=None,
        tags=None,
        relevant_files=None,
        id=None,
    ):
        if not id:
            id = uuid.uuid4().hex[:8]

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, description, status, priority, phase, phase_id, depends_on, acceptance, tags, relevant_files)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id,
                project_id,
                title,
                description,
                status,
                priority,
                phase,
                phase_id,
                depends_on,
                acceptance,
                ",".join(tags or []),
                _serialize_relevant_files(_normalize_relevant_files(relevant_files)),
            ),
        )
        conn.commit()
        conn.close()

        AuditLog.log("tasks", id, "create")

        return cls(
            id,
            project_id,
            title,
            description,
            status,
            priority,
            phase,
            phase_id,
            depends_on,
            acceptance,
            None,
            tags,
            relevant_files,
        )

    @classmethod
    def list_by_project(cls, project_id):
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM tasks WHERE project_id = ?", (project_id,)).fetchall()
        conn.close()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def get(cls, id):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (id,)).fetchone()
        conn.close()
        if row:
            return cls.from_row(row)
        return None

    @classmethod
    def get_next(cls, project_id: str, active_phase_id: str | None = None) -> "Task | None":
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
                return cls.from_row(row)

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
            return cls.from_row(row)
        return None

    @classmethod
    def _list_actionable_todo_rows(cls, project_id: str) -> list[Any]:
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

    @classmethod
    def _select_next_from_rows(cls, rows: list[Any]) -> "Task | None":
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
        return cls.from_row(ordered_rows[0])

    @classmethod
    def get_next_for_phase(
        cls,
        project_id: str,
        phase_id: str,
        phase_title: str,
    ) -> "Task | None":
        """Return the next actionable task linked to a phase by phase_id or legacy title."""
        normalized_title = _normalize_phase_title(phase_title)
        rows = [
            row
            for row in cls._list_actionable_todo_rows(project_id)
            if row["phase_id"] == phase_id
            or (not row["phase_id"] and _normalize_phase_title(row["phase"]) == normalized_title)
        ]
        return cls._select_next_from_rows(rows)

    @classmethod
    def get_next_unphased(cls, project_id: str) -> "Task | None":
        """Return the next actionable task with no first-class or legacy phase."""
        rows = [
            row
            for row in cls._list_actionable_todo_rows(project_id)
            if not row["phase_id"] and not _normalize_phase_title(row["phase"])
        ]
        return cls._select_next_from_rows(rows)

    @classmethod
    def count_by_status(cls, project_id: str) -> dict:
        """Return a dict of status → count for all tasks in the project."""
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM tasks WHERE project_id = ? GROUP BY status",
            (project_id,),
        ).fetchall()
        conn.close()
        return {row["status"]: row["cnt"] for row in rows}

    @classmethod
    def from_row(cls, row):
        relevant_files = []
        if "relevant_files" in row.keys():
            relevant_files = _deserialize_relevant_files(row["relevant_files"])
        return cls(
            row["id"],
            row["project_id"],
            row["title"],
            row["description"],
            row["status"],
            row["priority"],
            row["phase"],
            row["phase_id"],
            row["depends_on"],
            row["acceptance"],
            row["evidence"],
            row["tags"].split(",") if row["tags"] else [],
            relevant_files,
        )

    def update(self, **kwargs):
        updates = []
        params = []

        # Mapping model attributes to DB columns if they differ (here they match)
        for key, value in kwargs.items():
            if hasattr(self, key):
                old_value = getattr(self, key)
                new_value = value
                if key == "relevant_files":
                    new_value = _normalize_relevant_files(value)
                if old_value != new_value:
                    updates.append(f"{key} = ?")
                    if key == "relevant_files":
                        params.append(_serialize_relevant_files(new_value))
                    else:
                        params.append(value if not isinstance(value, list) else ",".join(value))
                    setattr(self, key, new_value)
                    AuditLog.log(
                        "tasks",
                        self.id,
                        "update",
                        field=key,
                        old_value=str(old_value),
                        new_value=str(new_value),
                    )

        if not updates:
            return

        updates.append("updated_at = datetime('now')")
        params.append(self.id)

        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        conn = get_db_connection()
        conn.execute(query, params)
        conn.commit()
        conn.close()

    def delete(self):
        conn = get_db_connection()
        conn.execute("DELETE FROM tasks WHERE id = ?", (self.id,))
        conn.commit()
        conn.close()
        AuditLog.log("tasks", self.id, "delete")


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
