"""Task model representing a persistent unit of work."""

from __future__ import annotations

import uuid

from engram.db import get_db_connection
from engram.models.audit import AuditLog
from engram.models.task import queries as _q
from engram.models.task.serialization import (
    deserialize_relevant_files,
    deserialize_search_hints,
    normalize_relevant_files,
    normalize_search_hints,
    serialize_relevant_files,
    serialize_search_hints,
)


class Task:
    @staticmethod
    def _prepare_create_fields(
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
        verification=None,
        search_hints=None,
        objective=None,
        is_verified=False,
    ):
        if description is None:
            description = objective
        if not id:
            id = uuid.uuid4().hex[:8]
        return (
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
            verification,
            serialize_search_hints(normalize_search_hints(search_hints)),
            1 if is_verified else 0,
        )

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
        verification=None,
        search_hints=None,
        is_verified=False,
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
        self.verification = verification
        self.search_hints = normalize_search_hints(search_hints)
        self.is_verified = bool(is_verified)

    @property
    def objective(self) -> str | None:
        """Alias for description/objective."""
        return self.description

    @objective.setter
    def objective(self, value: str | None) -> None:
        self.description = value

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
        verification=None,
        search_hints=None,
        objective=None,
        is_verified=False,
    ):
        params = cls._prepare_create_fields(
            project_id=project_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            phase=phase,
            phase_id=phase_id,
            depends_on=depends_on,
            acceptance=acceptance,
            tags=tags,
            relevant_files=relevant_files,
            memory_review_outcome=memory_review_outcome,
            id=id,
            verification=verification,
            search_hints=search_hints,
            objective=objective,
            is_verified=is_verified,
        )
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO tasks (id, project_id, title, description, status, priority, "
            "phase, phase_id, depends_on, acceptance, tags, relevant_files, memory_review_outcome, verification, search_hints, is_verified) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            params,
        )
        conn.commit()
        conn.close()
        task_id = params[0]
        AuditLog.log("tasks", task_id, "create")
        args = [
            task_id,
            project_id,
            title,
            params[3],
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
            verification,
            search_hints,
            is_verified,
        ]
        return cls(*args)

    @classmethod
    def create_many(cls, project_id: str, payloads: list[dict[str, object]]) -> list[Task]:
        insert_sql = (
            "INSERT INTO tasks (id, project_id, title, description, status, priority, "
            "phase, phase_id, depends_on, acceptance, tags, relevant_files, memory_review_outcome, "
            "verification, search_hints, is_verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        prepared_rows: list[tuple[object, ...]] = []
        created_tasks: list[Task] = []
        for payload in payloads:
            params = cls._prepare_create_fields(project_id=project_id, **payload)
            prepared_rows.append(params)
            created_tasks.append(
                cls(
                    id=params[0],
                    project_id=params[1],
                    title=params[2],
                    description=params[3],
                    status=params[4],
                    priority=params[5],
                    phase=params[6],
                    phase_id=params[7],
                    depends_on=params[8],
                    acceptance=params[9],
                    tags=(params[10].split(",") if params[10] else []),
                    relevant_files=deserialize_relevant_files(params[11]),
                    memory_review_outcome=params[12],
                    verification=params[13],
                    search_hints=deserialize_search_hints(params[14]),
                    is_verified=bool(params[15]),
                )
            )
        conn = get_db_connection()
        try:
            conn.execute("BEGIN")
            for row in prepared_rows:
                conn.execute(insert_sql, row)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        for task in created_tasks:
            AuditLog.log("tasks", task.id, "create")
        return created_tasks

    @classmethod
    def from_row(cls, row):
        rf = (
            deserialize_relevant_files(row["relevant_files"])
            if "relevant_files" in row.keys()
            else []
        )
        mro = row["memory_review_outcome"] if "memory_review_outcome" in row.keys() else None
        ver = row["verification"] if "verification" in row.keys() else None
        sh = deserialize_search_hints(row["search_hints"]) if "search_hints" in row.keys() else []
        is_verified = bool(row["is_verified"]) if "is_verified" in row.keys() else False
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
            ver,
            sh,
            is_verified,
        ]
        return cls(*args)

    def update(self, **kwargs):
        if "objective" in kwargs:
            kwargs["description"] = kwargs.pop("objective")

        # Material fields that affect execution or specifications make previous verification stale
        material_fields = {
            "title",
            "description",
            "acceptance",
            "relevant_files",
            "verification",
            "search_hints",
        }
        if any(f in kwargs for f in material_fields):
            kwargs["is_verified"] = False

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
            new = (
                normalize_relevant_files(val)
                if key == "relevant_files"
                else (normalize_search_hints(val) if key == "search_hints" else val)
            )
            if old != new:
                updates.append(f"{key} = ?")
                p_val = (
                    serialize_relevant_files(new)
                    if key == "relevant_files"
                    else (
                        serialize_search_hints(new)
                        if key == "search_hints"
                        else (
                            int(new)
                            if isinstance(new, bool)
                            else (val if not isinstance(val, list) else ",".join(val))
                        )
                    )
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
