"""Task model representing a persistent unit of work."""

from __future__ import annotations

import uuid

from engram.db import get_db_connection
from engram.models.audit import AuditLog
from engram.models.task import queries as _q
from engram.models.task.serialization import (
    deserialize_relevant_files,
    normalize_relevant_files,
    serialize_relevant_files,
)


class Task:
    def __init__(
        self,
        id,
        project_id,
        title,
        description=None,
        status="open",
        priority="medium",
        phase=None,
        phase_id=None,
        depends_on=None,
        acceptance=None,
        evidence=None,
        tags=None,
        relevant_files=None,
        memory_review_outcome=None,
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
        self.relevant_files = normalize_relevant_files(relevant_files)
        self.memory_review_outcome = memory_review_outcome

    @classmethod
    def create(
        cls,
        project_id,
        title,
        description=None,
        status="open",
        priority="medium",
        phase=None,
        phase_id=None,
        depends_on=None,
        acceptance=None,
        tags=None,
        relevant_files=None,
        memory_review_outcome=None,
        id=None,
    ):
        if not id:
            id = uuid.uuid4().hex[:8]

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO tasks (id, project_id, title, description, status, priority, "
            "phase, phase_id, depends_on, acceptance, tags, relevant_files, memory_review_outcome) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                serialize_relevant_files(normalize_relevant_files(relevant_files)),
                memory_review_outcome,
            ),
        )
        conn.commit()
        conn.close()

        AuditLog.log("tasks", id, "create")
        args = [
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
            memory_review_outcome,
        ]
        return cls(*args)

    @classmethod
    def from_row(cls, row):
        rf = (
            deserialize_relevant_files(row["relevant_files"])
            if "relevant_files" in row.keys()
            else []
        )
        mro = row["memory_review_outcome"] if "memory_review_outcome" in row.keys() else None
        args = [
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
            rf,
            mro,
        ]
        return cls(*args)

    def update(self, **kwargs):
        updates, params = [], []
        for key, val in kwargs.items():
            if not hasattr(self, key):
                continue
            old = getattr(self, key)
            if key == "status":
                if val in {"draft", "ready", "todo"}:
                    val = "open"
                elif val == "in-progress":
                    val = "in_progress"
            new = normalize_relevant_files(val) if key == "relevant_files" else val
            if old != new:
                updates.append(f"{key} = ?")
                p_val = (
                    serialize_relevant_files(new)
                    if key == "relevant_files"
                    else (val if not isinstance(val, list) else ",".join(val))
                )
                params.append(p_val)
                setattr(self, key, new)
                AuditLog.log(
                    "tasks", self.id, "update", field=key, old_value=str(old), new_value=str(new)
                )
        if updates:
            updates.append("updated_at = datetime('now')")
            params.append(self.id)
            conn = get_db_connection()
            conn.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            conn.close()

    def delete(self):
        conn = get_db_connection()
        conn.execute("DELETE FROM tasks WHERE id = ?", (self.id,))
        conn.commit()
        conn.close()
        AuditLog.log("tasks", self.id, "delete")

    @classmethod
    def list_by_project(cls, project_id: str) -> list[Task]:
        return _q.list_by_project(project_id)

    @classmethod
    def get(cls, id: str) -> Task | None:
        return _q.get(id)

    @classmethod
    def get_next(cls, project_id: str, active_phase_id: str | None = None) -> Task | None:
        return _q.get_next(project_id, active_phase_id)

    @classmethod
    def get_next_for_phase(cls, project_id: str, phase_id: str, phase_title: str) -> Task | None:
        return _q.get_next_for_phase(project_id, phase_id, phase_title)

    @classmethod
    def get_next_unphased(cls, project_id: str) -> Task | None:
        return _q.get_next_unphased(project_id)

    @classmethod
    def count_by_status(cls, project_id: str) -> dict[str, int]:
        return _q.count_by_status(project_id)
