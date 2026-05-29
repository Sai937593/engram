import json
import uuid
from typing import Any

from engram.db import get_db_connection
from engram.models.audit import AuditLog


def _normalize_relevant_files(relevant_files: Any) -> list[str]:
    """Normalize relevant file paths by trimming entries, dropping empties, and deduplicating."""
    if relevant_files is None:
        return []
    if isinstance(relevant_files, str):
        candidates = [relevant_files]
    else:
        candidates = list(relevant_files)

    normalized: list[str] = []
    seen: set[str] = set()
    for path in candidates:
        if path is None:
            continue
        cleaned = str(path).strip()
        if cleaned and cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)
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

    @classmethod
    def list_by_project(cls, project_id: str) -> list["Task"]:
        from engram.models.task.queries import list_by_project

        return list_by_project(project_id)

    @classmethod
    def get(cls, id: str) -> "Task | None":
        from engram.models.task.queries import get

        return get(id)

    @classmethod
    def get_next(cls, project_id: str, active_phase_id: str | None = None) -> "Task | None":
        from engram.models.task.queries import get_next

        return get_next(project_id, active_phase_id)

    @classmethod
    def get_next_for_phase(cls, project_id: str, phase_id: str, phase_title: str) -> "Task | None":
        from engram.models.task.queries import get_next_for_phase

        return get_next_for_phase(project_id, phase_id, phase_title)

    @classmethod
    def get_next_unphased(cls, project_id: str) -> "Task | None":
        from engram.models.task.queries import get_next_unphased

        return get_next_unphased(project_id)

    @classmethod
    def count_by_status(cls, project_id: str) -> dict[str, int]:
        from engram.models.task.queries import count_by_status

        return count_by_status(project_id)
