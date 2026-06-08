"""Plan model representing a first-class implementation plan."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from engram.db import get_db_connection
from engram.models.audit import AuditLog


from engram.models.project_helpers import optional_text as _optional_text


def _required_text(value: Any, field_name: str) -> str:
    """Return a stripped text value or raise if it is missing."""
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required.")
    return text



class Plan:
    """Persistent implementation plan record."""

    VALID_STATUSES = {"draft", "active", "review_pending", "done", "archived", "cancelled"}

    def __init__(
        self, id: str, project_id: str, title: str, slug: str | None = None,
        status: str = "draft", source_doc_path: str | None = None, key: str | None = None,
        created_at: str | None = None, updated_at: str | None = None,
    ) -> None:
        self.id = id
        self.project_id = project_id
        self.key = id if key is None else key
        self.title = title
        self.slug = slug
        self.status = status
        self.source_doc_path = source_doc_path
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(
        cls, project_id: str, title: str, slug: str | None = None, status: str = "draft",
        source_doc_path: str | None = None, id: str | None = None, key: str | None = None,
        db_path: str | Path | None = None,
    ) -> Plan:
        """Create a new plan record and return the persisted model."""
        resolved_project_id = _required_text(project_id, "project_id")
        resolved_title = _required_text(title, "title")
        resolved_status = cls._validate_status(status)
        resolved_slug = _optional_text(slug)
        resolved_source_doc_path = _optional_text(source_doc_path)
        plan_id = id.strip() if isinstance(id, str) and id.strip() else uuid.uuid4().hex[:8]
        plan_key = key.strip() if isinstance(key, str) and key.strip() else plan_id

        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        existing = conn.execute(
            "SELECT id FROM plans WHERE project_id = ? AND key = ?",
            (resolved_project_id, plan_key),
        ).fetchone()
        if existing and existing["id"] != plan_id:
            conn.close()
            raise ValueError(f"Plan key '{plan_key}' already exists in this project.")

        conn.execute(
            "INSERT INTO plans (id, project_id, key, title, slug, status, source_doc_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (plan_id, resolved_project_id, plan_key, resolved_title, resolved_slug, resolved_status, resolved_source_doc_path),
        )
        row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        conn.commit()
        conn.close()
        AuditLog.log("plans", plan_id, "create")

        if row is None:
            raise ValueError(f"Plan '{plan_id}' was not persisted.")
        return cls.from_row(row)


    @classmethod
    def get(cls, id: str, db_path: str | Path | None = None) -> Plan | None:
        """Return a plan by its internal ID."""
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        row = conn.execute("SELECT * FROM plans WHERE id = ?", (id,)).fetchone()
        conn.close()
        return cls.from_row(row) if row else None

    @classmethod
    def get_by_key(
        cls, project_id: str, key: str, db_path: str | Path | None = None
    ) -> Plan | None:
        """Return a plan by project-scoped key."""
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        row = conn.execute(
            "SELECT * FROM plans WHERE project_id = ? AND key = ?",
            (project_id, key),
        ).fetchone()
        conn.close()
        return cls.from_row(row) if row else None

    @classmethod
    def list_by_project(cls, project_id: str, db_path: str | Path | None = None) -> list[Plan]:
        """Return all plans for one project ordered by creation time."""
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        rows = conn.execute(
            "SELECT * FROM plans WHERE project_id = ? ORDER BY created_at ASC, id ASC",
            (project_id,),
        ).fetchall()
        conn.close()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def from_row(cls, row: Any) -> Plan:
        """Build a Plan from a SQLite row."""
        k = row.keys()
        slug = row["slug"] if "slug" in k else None
        sd = row["source_doc_path"] if "source_doc_path" in k else None
        key = row["key"] if "key" in k else row["id"]
        cat = row["created_at"] if "created_at" in k else None
        uat = row["updated_at"] if "updated_at" in k else None
        return cls(
            row["id"],
            row["project_id"],
            row["title"],
            slug,
            row["status"],
            sd,
            key,
            cat,
            uat,
        )


    @classmethod
    def _validate_status(cls, status: str) -> str:
        """Validate and normalize plan status values."""
        normalized = _required_text(status, "status")
        if normalized not in cls.VALID_STATUSES:
            allowed = ", ".join(sorted(cls.VALID_STATUSES))
            raise ValueError(f"Invalid plan status '{normalized}'. Allowed statuses: {allowed}.")
        return normalized

    def update(
        self,
        title: str | None = None,
        slug: str | None = None,
        status: str | None = None,
        source_doc_path: str | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        """Update mutable plan fields in database and in-memory model."""
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        updates = []
        params = []

        def upd(field: str, val: Any, required: bool = False) -> None:
            val_text = _required_text(val, field) if required else _optional_text(val)
            old_val = getattr(self, field)
            if old_val != val_text:
                updates.append(f"{field} = ?")
                params.append(val_text)
                setattr(self, field, val_text)
                AuditLog.log(
                    "plans",
                    self.id,
                    "update",
                    field=field,
                    old_value=old_val,
                    new_value=val_text,
                    conn=conn,
                )

        if title is not None:
            upd("title", title, required=True)
        if slug is not None:
            upd("slug", slug)
        if status is not None:
            upd("status", self._validate_status(status), required=True)
        if source_doc_path is not None:
            upd("source_doc_path", source_doc_path)

        if not updates:
            conn.close()
            return

        updates.append("updated_at = datetime('now')")
        params.append(self.id)

        query = f"UPDATE plans SET {', '.join(updates)} WHERE id = ?"
        conn.execute(query, params)
        conn.commit()
        conn.close()

