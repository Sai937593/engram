import uuid
from typing import Any

from engram.db import get_db_connection
from engram.models.audit import AuditLog


class Phase:
    """Domain model for project phases."""

    VALID_STATUSES = {"planned", "active", "done", "blocked", "cancelled"}

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
    ) -> None:
        self.id = id
        self.project_id = project_id
        self.title = title
        self.description = description
        self.status = status
        self.order_index = order_index
        self.acceptance = acceptance
        self.evidence = evidence

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
    ) -> "Phase":
        """Create and persist a phase."""
        cls._validate_status(status)
        phase_id = id or uuid.uuid4().hex[:8]

        conn = get_db_connection()
        resolved_order_index = order_index
        if resolved_order_index is None:
            row = conn.execute(
                """
                SELECT COALESCE(MAX(order_index), -1) + 1 AS next_order_index
                FROM phases
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()
            resolved_order_index = int(row["next_order_index"])

        conn.execute(
            """
            INSERT INTO phases (id, project_id, title, description, status, order_index, acceptance, evidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                phase_id,
                project_id,
                title,
                description,
                status,
                resolved_order_index,
                acceptance,
                evidence,
            ),
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
        )

    @classmethod
    def get(cls, id: str) -> "Phase | None":
        """Get a phase by id."""
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM phases WHERE id = ?", (id,)).fetchone()
        conn.close()
        if row:
            return cls.from_row(row)
        return None

    @classmethod
    def list_by_project(cls, project_id: str) -> list["Phase"]:
        """List project phases ordered by index."""
        conn = get_db_connection()
        rows = conn.execute(
            """
            SELECT * FROM phases
            WHERE project_id = ?
            ORDER BY order_index ASC, created_at ASC
            """,
            (project_id,),
        ).fetchall()
        conn.close()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def from_row(cls, row: Any) -> "Phase":
        """Build a Phase object from a database row."""
        return cls(
            row["id"],
            row["project_id"],
            row["title"],
            row["description"],
            row["status"],
            row["order_index"],
            row["acceptance"],
            row["evidence"],
        )

    def update(self, **kwargs: Any) -> None:
        """Update mutable phase fields."""
        updates = []
        params = []
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
                updates.append(f"{key} = ?")
                params.append(value)
                setattr(self, key, value)
                AuditLog.log(
                    "phases",
                    self.id,
                    "update",
                    field=key,
                    old_value=str(old_value),
                    new_value=str(value),
                )

        if not updates:
            return

        updates.append("updated_at = datetime('now')")
        params.append(self.id)

        conn = get_db_connection()
        conn.execute(f"UPDATE phases SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        conn.close()

    @classmethod
    def _validate_status(cls, status: str) -> None:
        if status not in cls.VALID_STATUSES:
            allowed = ", ".join(sorted(cls.VALID_STATUSES))
            raise ValueError(f"Invalid phase status '{status}'. Allowed statuses: {allowed}.")
