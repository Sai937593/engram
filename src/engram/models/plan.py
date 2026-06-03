"""Plan model representing a first-class implementation plan."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from engram.db import get_db_connection
from engram.models.audit import AuditLog


def _required_text(value: Any, field_name: str) -> str:
    """Return a stripped text value or raise if it is missing."""
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"{field_name} is required.")
    return text


def _optional_text(value: Any) -> str | None:
    """Normalize blank optional values to None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class Plan:
    """Persistent implementation plan record."""

    VALID_STATUSES = {"draft", "active", "review_pending", "done", "archived", "cancelled"}

    def __init__(
        self,
        id: str,
        project_id: str,
        title: str,
        slug: str | None = None,
        status: str = "draft",
        source_doc_path: str | None = None,
        key: str | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
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
        cls,
        project_id: str,
        title: str,
        slug: str | None = None,
        status: str = "draft",
        source_doc_path: str | None = None,
        id: str | None = None,
        key: str | None = None,
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
            """
            INSERT INTO plans (id, project_id, key, title, slug, status, source_doc_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id,
                resolved_project_id,
                plan_key,
                resolved_title,
                resolved_slug,
                resolved_status,
                resolved_source_doc_path,
            ),
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
        if row is None:
            return None
        return cls.from_row(row)

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
        if row is None:
            return None
        return cls.from_row(row)

    @classmethod
    def list_by_project(cls, project_id: str, db_path: str | Path | None = None) -> list[Plan]:
        """Return all plans for one project ordered by creation time."""
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        rows = conn.execute(
            """
            SELECT * FROM plans
            WHERE project_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (project_id,),
        ).fetchall()
        conn.close()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def from_row(cls, row: Any) -> Plan:
        """Build a Plan from a SQLite row."""
        return cls(
            row["id"],
            row["project_id"],
            row["title"],
            row["slug"] if "slug" in row.keys() else None,
            row["status"],
            row["source_doc_path"] if "source_doc_path" in row.keys() else None,
            row["key"] if "key" in row.keys() else row["id"],
            row["created_at"] if "created_at" in row.keys() else None,
            row["updated_at"] if "updated_at" in row.keys() else None,
        )

    @classmethod
    def _validate_status(cls, status: str) -> str:
        """Validate and normalize plan status values."""
        normalized = _required_text(status, "status")
        if normalized not in cls.VALID_STATUSES:
            allowed = ", ".join(sorted(cls.VALID_STATUSES))
            raise ValueError(f"Invalid plan status '{normalized}'. Allowed statuses: {allowed}.")
        return normalized
