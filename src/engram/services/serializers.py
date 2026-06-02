"""JSON-safe serializers for service-layer DTOs."""

from __future__ import annotations

from typing import Any

from engram.models.memory import Memory
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task, get_effective_phase_title
from engram.services.errors import JsonValue


def _none_if_blank(value: Any) -> str | None:
    """Return None for missing or blank string values."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _string_list(value: Any) -> list[str]:
    """Normalize list-like values into a JSON-safe list of strings."""
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        source = value
    else:
        source = [value]

    normalized: list[str] = []
    for item in source:
        if item is None:
            continue
        cleaned = str(item).strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def _get_effective_status(task: Task) -> str:
    """Compute dependency-aware status without importing CLI helpers."""
    status = task.status
    if status in {"draft", "ready", "todo"}:
        status = "open"
    elif status == "in-progress":
        status = "in_progress"

    if status in {"done", "cancelled"}:
        return status

    visited: set[str] = set()
    current = task
    has_unfinished = False
    has_blocked = False

    while current.depends_on:
        dep_id = current.depends_on
        if dep_id in visited:
            break
        visited.add(dep_id)

        dependency = Task.get(dep_id)
        if not dependency:
            break
        dep_status = dependency.status
        if dep_status in {"draft", "ready", "todo"}:
            dep_status = "open"
        elif dep_status == "in-progress":
            dep_status = "in_progress"

        if dep_status == "cancelled":
            return "cancelled"
        if dep_status == "blocked":
            has_blocked = True
        elif dep_status != "done":
            has_unfinished = True
        current = dependency

    if has_blocked or has_unfinished:
        return "blocked"
    return status


def project_to_dict(project: Project) -> dict[str, JsonValue]:
    """Serialize a Project model into a JSON-safe dictionary."""
    return {
        "id": str(project.id),
        "plan_key": _none_if_blank(getattr(project, "plan_key", None) or project.id),
        "name": str(project.name),
        "summary": _none_if_blank(project.summary),
        "status": str(project.status),
        "repo_paths": _string_list(project.repo_paths),
    }


def task_to_dict(task: Task, *, compact: bool = False) -> dict[str, JsonValue]:
    """Serialize a Task model into a JSON-safe dictionary."""
    phase = None
    if task.phase_id:
        phase = Phase.get(task.phase_id)
    payload: dict[str, JsonValue] = {
        "id": str(task.id),
        "project_id": str(task.project_id),
        "key": _none_if_blank(getattr(task, "key", None) or task.id),
        "title": str(task.title),
        "description": _none_if_blank(task.description),
        "objective": _none_if_blank(task.description),
        "status": str(task.status),
        "effective_status": _get_effective_status(task),
        "priority": str(task.priority),
        "phase": _none_if_blank(task.phase),
        "phase_id": _none_if_blank(task.phase_id),
        "phase_key": _none_if_blank(getattr(phase, "key", None) if phase else None),
        "phase_title": _none_if_blank(get_effective_phase_title(task)),
        "depends_on": _none_if_blank(task.depends_on),
        "acceptance": _none_if_blank(task.acceptance),
        "evidence": _none_if_blank(task.evidence),
        "tags": _string_list(task.tags),
        "relevant_files": _string_list(task.relevant_files),
        "verification": _none_if_blank(task.verification),
        "search_hints": _string_list(task.search_hints),
        "memory_review_outcome": _none_if_blank(task.memory_review_outcome),
        "is_verified": bool(task.is_verified),
    }
    if not compact:
        return payload
    return {
        "id": payload["id"],
        "key": payload["key"],
        "title": payload["title"],
        "status": payload["status"],
        "phase_id": payload["phase_id"],
        "phase_key": payload["phase_key"],
        "phase_title": payload["phase_title"],
        "is_verified": payload["is_verified"],
    }


def memory_to_dict(memory: Memory) -> dict[str, JsonValue]:
    """Serialize a Memory model into a JSON-safe dictionary."""
    return {
        "id": str(memory.id),
        "project_id": str(memory.project_id),
        "type": str(memory.type),
        "title": str(memory.title),
        "content": str(memory.content),
        "scope": str(memory.scope),
        "task_id": _none_if_blank(memory.task_id),
        "tags": _string_list(memory.tags),
        "always_include": bool(memory.always_include),
        "level": _none_if_blank(memory.level),
        "superseded_by": _none_if_blank(getattr(memory, "superseded_by", None)),
    }


def compact_memory_to_dict(
    memory: Memory, *, created_at: str | None = None, updated_at: str | None = None
) -> dict[str, JsonValue]:
    """Serialize a Memory model into a compact agent-facing dictionary."""
    content = str(memory.content)
    preview = content if len(content) <= 240 else f"{content[:237]}..."
    return {
        "id": str(memory.id),
        "title": str(memory.title),
        "content": content,
        "content_preview": preview,
        "created_at": _none_if_blank(created_at),
        "updated_at": _none_if_blank(updated_at),
    }


def phase_to_dict(phase: Phase) -> dict[str, JsonValue]:
    """Serialize a Phase model into a JSON-safe dictionary."""
    payload: dict[str, JsonValue] = {
        "id": str(phase.id),
        "project_id": str(phase.project_id),
        "key": _none_if_blank(getattr(phase, "key", None) or phase.id),
        "title": str(phase.title),
        "description": _none_if_blank(phase.description),
        "status": str(phase.status),
        "order_index": int(phase.order_index),
        "acceptance": _none_if_blank(phase.acceptance),
        "evidence": _none_if_blank(phase.evidence),
    }
    if phase.status_label != phase.status:
        payload["status_label"] = phase.status_label
    return payload
