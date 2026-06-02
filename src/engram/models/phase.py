import uuid
from typing import Any

from engram.db import get_db_connection
from engram.models.audit import AuditLog
from engram.models.phase_lifecycle import start_phase as start_phase_transition
from engram.models.phase_persistence import (
    delete_phase_row,
    fetch_phase_row,
    fetch_project_phase_rows,
    insert_phase,
    resolve_next_order_index,
    update_phase_fields,
)


class Phase:
    VALID_STATUSES = {"planned", "active", "review_pending", "done", "blocked", "cancelled"}
    STATUS_LABELS = {"review_pending": "To be reviewed"}

    def __init__(
        self,
        id: str,
        project_id: str,
        title: str,
        description: str | None = None,
        status: str = "planned",
        order_index: int = 0,
        acceptance: str | None = None,
        evidence: str | None = None,
        key: str | None = None,
    ) -> None:
        self.id = id
        self.project_id = project_id
        self.key = id if key is None else key
        self.title = title
        self.description = description
        self.status = status
        self.order_index = order_index
        self.acceptance = acceptance
        self.evidence = evidence

    @property
    def status_label(self) -> str:
        return self.STATUS_LABELS.get(self.status, self.status)

    @classmethod
    def create(
        cls,
        project_id: str,
        title: str,
        description: str | None = None,
        status: str = "planned",
        order_index: int | None = None,
        acceptance: str | None = None,
        evidence: str | None = None,
        id: str | None = None,
        key: str | None = None,
    ) -> "Phase":
        cls._validate_status(status)
        phase_id = id or uuid.uuid4().hex[:8]
        phase_key = key.strip() if isinstance(key, str) and key.strip() else phase_id

        existing_keys = {
            phase.key
            for phase in cls.list_by_project(project_id)
            if phase.key and phase.id != phase_id
        }
        if phase_key in existing_keys:
            raise ValueError(f"Phase key '{phase_key}' already exists in this project.")

        conn = get_db_connection()
        resolved_order_index = order_index
        if resolved_order_index is None:
            resolved_order_index = resolve_next_order_index(conn, project_id)

        insert_phase(
            conn=conn,
            phase_id=phase_id,
            project_id=project_id,
            key=phase_key,
            title=title,
            description=description,
            status=status,
            order_index=resolved_order_index,
            acceptance=acceptance,
            evidence=evidence,
        )
        conn.commit()
        conn.close()

        AuditLog.log("phases", phase_id, "create")

        return cls(
            phase_id,
            project_id,
            title,
            description,
            status,
            int(resolved_order_index),
            acceptance,
            evidence,
            phase_key,
        )

    @classmethod
    def get(cls, id: str) -> "Phase | None":
        conn = get_db_connection()
        row = fetch_phase_row(conn, id)
        conn.close()
        if row:
            return cls.from_row(row)
        return None

    @classmethod
    def list_by_project(cls, project_id: str) -> list["Phase"]:
        conn = get_db_connection()
        rows = fetch_project_phase_rows(conn, project_id)
        conn.close()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def from_row(cls, row: Any) -> "Phase":
        return cls(
            row["id"],
            row["project_id"],
            row["title"],
            row["description"],
            row["status"],
            row["order_index"],
            row["acceptance"],
            row["evidence"],
            row["key"] if "key" in row.keys() else row["id"],
        )

    def update(self, **kwargs: Any) -> None:
        pending_updates: dict[str, Any] = {}
        allowed_fields = {"title", "description", "status", "order_index", "acceptance", "evidence"}

        for key, value in kwargs.items():
            if key not in allowed_fields:
                continue
            if key == "status" and value is not None:
                self._validate_status(value)
            if key == "order_index" and value is not None:
                value = int(value)

            old_value = getattr(self, key)
            if old_value != value:
                pending_updates[key] = value
                setattr(self, key, value)
                AuditLog.log(
                    "phases",
                    self.id,
                    "update",
                    field=key,
                    old_value=str(old_value),
                    new_value=str(value),
                )

        if not pending_updates:
            return

        conn = get_db_connection()
        update_phase_fields(conn, self.id, pending_updates)
        conn.commit()
        conn.close()

    def delete(self) -> None:
        conn = get_db_connection()
        delete_phase_row(conn, self.id)
        conn.commit()
        conn.close()
        AuditLog.log("phases", self.id, "delete")

    @classmethod
    def start(cls, phase_id: str) -> tuple["Phase", int]:
        phase = cls.get(phase_id)
        if phase is None:
            raise ValueError(f"Phase '{phase_id}' not found.")
        demoted_count = start_phase_transition(phase.id, phase.project_id, phase.status)

        refreshed = cls.get(phase.id)
        if refreshed is None:
            raise ValueError(f"Phase '{phase_id}' not found after update.")
        return refreshed, demoted_count

    @classmethod
    def _validate_status(cls, status: str) -> None:
        if status not in cls.VALID_STATUSES:
            allowed = ", ".join(sorted(cls.VALID_STATUSES))
            raise ValueError(f"Invalid phase status '{status}'. Allowed statuses: {allowed}.")
