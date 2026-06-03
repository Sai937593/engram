"""Helpers for project model normalization and validation."""

from __future__ import annotations

import json
from typing import Any


def optional_text(value: Any) -> str | None:
    """Normalize blank optional text to None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def plan_key_or_default(value: Any, default: str) -> str:
    """Return a normalized plan key or the provided default value."""
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def load_repo_paths(value: str | None) -> list[str]:
    """Return a normalized repo path list from the stored JSON payload."""
    if not value:
        return []
    return json.loads(value)


def validate_active_plan(conn, project_id: str, active_plan_id: str) -> None:
    """Ensure the active plan exists and belongs to the project."""
    row = conn.execute(
        "SELECT id, project_id FROM plans WHERE id = ?",
        (active_plan_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Active plan '{active_plan_id}' does not exist.")
    if row["project_id"] != project_id:
        raise ValueError(
            f"Active plan '{active_plan_id}' does not belong to project '{project_id}'."
        )
