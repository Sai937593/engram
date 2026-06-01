"""Maintenance lifecycle operations for task state transitions."""

from __future__ import annotations

from datetime import datetime

from engram.models.task import Task
from engram.services.errors import EngramServiceError, ValidationError
from engram.services.serializers import task_to_dict
from engram.services.task.validation import resolve_task_ref


def _get_task(project_id: str, task_ref: str) -> Task:
    task_id = resolve_task_ref(project_id, task_ref)
    task_item = Task.get(task_id)
    if task_item is None:
        raise EngramServiceError(
            code="TASK_NOT_FOUND",
            message="Task reference was not found in this project.",
            details={"project_id": project_id, "task_ref": task_ref.strip()},
        )
    return task_item


def _raise_invalid_transition(task_item: Task, target: str) -> None:
    raise ValidationError(
        code="INVALID_TASK_TRANSITION",
        message=f"Cannot transition task '{task_item.id}' from '{task_item.status}' to '{target}'.",
        details={"task_id": task_item.id, "from_status": task_item.status, "to_status": target},
    )


def _append_evidence(task_item: Task, evidence: str | None) -> str | None:
    if not evidence or not evidence.strip():
        return task_item.evidence
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"[{timestamp}] {evidence.strip()}"
    existing = task_item.evidence or ""
    return (existing + "\n" + new_entry).strip() if existing else new_entry


def block_task(project_id: str, task_ref: str, reason: str | None = None) -> dict[str, object]:
    """Block a task and optionally append blocking context into evidence."""
    task_item = _get_task(project_id, task_ref)
    if task_item.status in {"done", "cancelled", "blocked"}:
        _raise_invalid_transition(task_item, "blocked")
    task_item.update(status="blocked", evidence=_append_evidence(task_item, reason))
    return task_to_dict(task_item)


def unblock_task(
    project_id: str,
    task_ref: str,
    target_status: str = "todo",
    note: str | None = None,
) -> dict[str, object]:
    """Unblock a blocked task back into a planned status."""
    task_item = _get_task(project_id, task_ref)
    if task_item.status != "blocked":
        _raise_invalid_transition(task_item, target_status)
    if target_status not in {"draft", "ready", "todo"}:
        raise ValidationError(
            code="INVALID_TASK_TRANSITION_TARGET",
            message="Unblock target status must be draft, ready, or todo.",
            details={
                "task_id": task_item.id,
                "target_status": target_status,
                "allowed_targets": ["draft", "ready", "todo"],
            },
        )
    task_item.update(status=target_status, evidence=_append_evidence(task_item, note))
    return task_to_dict(task_item)


def cancel_task(project_id: str, task_ref: str, reason: str | None = None) -> dict[str, object]:
    """Cancel a task from non-terminal states."""
    task_item = _get_task(project_id, task_ref)
    if task_item.status in {"done", "cancelled"}:
        _raise_invalid_transition(task_item, "cancelled")
    task_item.update(status="cancelled", evidence=_append_evidence(task_item, reason))
    return task_to_dict(task_item)


def retire_task(project_id: str, task_ref: str, reason: str | None = None) -> dict[str, object]:
    """Retire a task by deleting it once it has reached a terminal state."""
    task_item = _get_task(project_id, task_ref)
    if task_item.status not in {"done", "cancelled"}:
        _raise_invalid_transition(task_item, "deleted")
    if reason and reason.strip():
        task_item.update(evidence=_append_evidence(task_item, reason))
    payload = task_to_dict(task_item)
    task_item.delete()
    return {"deleted": True, "task": payload}
