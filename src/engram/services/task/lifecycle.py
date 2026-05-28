"""Lifecycle operations for tasks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from engram.models.task import Task
from engram.services.errors import EngramServiceError, ValidationError
from engram.services.serializers import task_to_dict
from engram.services.task.validation import resolve_task_ref


def get_next_task(project_id: str) -> dict[str, object] | None:
    """Return the next actionable task as a JSON-safe DTO, if one exists."""
    next_task = Task.get_next(project_id)
    if next_task is None:
        return None
    return task_to_dict(next_task)


def start_task(project_id: str, task_ref: str) -> dict[str, object]:
    """Start a task by marking it in-progress, validating its dependencies."""
    task_id = resolve_task_ref(project_id, task_ref)
    task_item = Task.get(task_id)
    if task_item is None:
        raise EngramServiceError(
            code="TASK_NOT_FOUND",
            message="Task reference was not found in this project.",
            details={"project_id": project_id, "task_ref": task_ref.strip()},
        )

    # Validate dependencies
    if task_item.depends_on:
        dep_task = Task.get(task_item.depends_on)
        if dep_task and dep_task.status != "done":
            raise ValidationError(
                code="DEPENDENCY_UNSATISFIED",
                message=f"Cannot start task '{task_item.title}' because its dependency '{dep_task.title}' ({dep_task.id}) is not done.",
                details={
                    "task_id": task_item.id,
                    "depends_on": task_item.depends_on,
                    "dependency_status": dep_task.status,
                },
            )

    task_item.update(status="in-progress")
    return task_to_dict(task_item)


def complete_task(
    project_id: str,
    task_ref: str,
    evidence: str | None = None,
) -> dict[str, object]:
    """Complete a task by marking it done, optionally appending evidence."""
    task_id = resolve_task_ref(project_id, task_ref)
    task_item = Task.get(task_id)
    if task_item is None:
        raise EngramServiceError(
            code="TASK_NOT_FOUND",
            message="Task reference was not found in this project.",
            details={"project_id": project_id, "task_ref": task_ref.strip()},
        )

    updates: dict[str, Any] = {"status": "done"}
    if evidence and evidence.strip():
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_entry = f"[{timestamp}] {evidence.strip()}"
        existing = task_item.evidence or ""
        updates["evidence"] = (existing + "\n" + new_entry).strip() if existing else new_entry

    task_item.update(**updates)
    return task_to_dict(task_item)
