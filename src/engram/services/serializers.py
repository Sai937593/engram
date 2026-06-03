"""JSON-safe serializers for service-layer DTOs."""

from __future__ import annotations

from engram.models.memory import Memory
from engram.models.phase import Phase
from engram.models.plan import Plan
from engram.models.project import Project
from engram.models.task import Task, get_effective_phase_title
from engram.services.errors import JsonValue
from engram.services.serializer_helpers import get_effective_status, none_if_blank, string_list


def project_to_dict(project: Project) -> dict[str, JsonValue]:
    """Serialize a Project model into a JSON-safe dictionary."""
    return {
        "id": str(project.id),
        "plan_key": none_if_blank(getattr(project, "plan_key", None) or project.id),
        "name": str(project.name),
        "summary": none_if_blank(project.summary),
        "status": str(project.status),
        "repo_paths": string_list(project.repo_paths),
    }


def plan_to_dict(plan: Plan) -> dict[str, JsonValue]:
    """Serialize a Plan model into a JSON-safe dictionary."""
    return {
        "id": str(plan.id),
        "project_id": str(plan.project_id),
        "key": none_if_blank(getattr(plan, "key", None) or plan.id),
        "title": str(plan.title),
        "slug": none_if_blank(plan.slug),
        "status": str(plan.status),
        "source_doc_path": none_if_blank(plan.source_doc_path),
        "created_at": none_if_blank(plan.created_at),
        "updated_at": none_if_blank(plan.updated_at),
    }


def task_to_dict(task: Task, *, compact: bool = False) -> dict[str, JsonValue]:
    """Serialize a Task model into a JSON-safe dictionary."""
    phase = Phase.get(task.phase_id) if task.phase_id else None
    payload: dict[str, JsonValue] = {
        "id": str(task.id),
        "project_id": str(task.project_id),
        "key": none_if_blank(getattr(task, "key", None) or task.id),
        "title": str(task.title),
        "description": none_if_blank(task.description),
        "objective": none_if_blank(task.description),
        "status": str(task.status),
        "effective_status": get_effective_status(task),
        "priority": str(task.priority),
        "phase": none_if_blank(task.phase),
        "phase_id": none_if_blank(task.phase_id),
        "phase_key": none_if_blank(getattr(phase, "key", None) if phase else None),
        "phase_title": none_if_blank(get_effective_phase_title(task)),
        "depends_on": none_if_blank(task.depends_on),
        "acceptance": none_if_blank(task.acceptance),
        "evidence": none_if_blank(task.evidence),
        "tags": string_list(task.tags),
        "relevant_files": string_list(task.relevant_files),
        "verification": none_if_blank(task.verification),
        "search_hints": string_list(task.search_hints),
        "memory_review_outcome": none_if_blank(task.memory_review_outcome),
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


def memory_to_dict(memory: Memory, *, include_lifecycle: bool = False) -> dict[str, JsonValue]:
    """Serialize a Memory model into a JSON-safe dictionary."""
    payload: dict[str, JsonValue] = {
        "id": str(memory.id),
        "project_id": str(memory.project_id),
        "type": str(memory.type),
        "title": str(memory.title),
        "content": str(memory.content),
        "scope": str(memory.scope),
        "task_id": none_if_blank(memory.task_id),
        "tags": string_list(memory.tags),
        "always_include": bool(memory.always_include),
        "level": none_if_blank(memory.level),
    }
    if include_lifecycle:
        payload["superseded_by"] = none_if_blank(getattr(memory, "superseded_by", None))
    return payload


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
        "created_at": none_if_blank(created_at),
        "updated_at": none_if_blank(updated_at),
    }


def phase_to_dict(
    phase: Phase,
    *,
    compact: bool = False,
    markers: dict[str, bool] | None = None,
) -> dict[str, JsonValue]:
    """Serialize a Phase model into a JSON-safe dictionary."""
    if compact:
        payload: dict[str, JsonValue] = {
            "id": str(phase.id),
            "key": none_if_blank(getattr(phase, "key", None) or phase.id),
            "title": str(phase.title),
            "status": str(phase.status),
        }
    else:
        payload = {
            "id": str(phase.id),
            "project_id": str(phase.project_id),
            "key": none_if_blank(getattr(phase, "key", None) or phase.id),
            "title": str(phase.title),
            "description": none_if_blank(phase.description),
            "status": str(phase.status),
            "order_index": int(phase.order_index),
            "acceptance": none_if_blank(phase.acceptance),
            "evidence": none_if_blank(phase.evidence),
        }
        if phase.status_label != phase.status:
            payload["status_label"] = phase.status_label
    if markers:
        payload.update(markers)
    return payload
