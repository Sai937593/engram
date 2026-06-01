"""Memory service lifecycle operations."""

from __future__ import annotations

from engram.services.errors import JsonValue, ValidationError
from engram.services.memory_service import create_memory
from engram.services.memory_update_support import get_project_memory
from engram.services.serializers import memory_to_dict


def supersede_memory(
    project_id: str,
    memory_ref: str,
    *,
    title: str,
    content: str,
    type: str | None = None,
    scope: str | None = None,
    task_id: str | None = None,
    tags: list[str] | None = None,
    always_include: bool | None = None,
    level: str | None = None,
    id: str | None = None,
) -> dict[str, JsonValue]:
    """Create a replacement memory and mark the source memory as superseded."""
    source = get_project_memory(project_id, memory_ref)
    if source.superseded_by is not None:
        raise ValidationError(
            code="MEMORY_ALREADY_SUPERSEDED",
            message="Cannot supersede a memory that is already superseded or archived.",
            details={"memory_ref": source.id, "superseded_by": source.superseded_by},
        )
    return create_memory(
        project_id=project_id,
        type=type or source.type,
        title=title,
        content=content,
        scope=scope or source.scope,
        task_id=source.task_id if task_id is None else task_id,
        tags=source.tags if tags is None else tags,
        always_include=source.always_include if always_include is None else always_include,
        level=source.level if level is None else level,
        id=id,
        supersedes=source.id,
    )


def demote_memory(project_id: str, memory_ref: str, *, reason: str) -> dict[str, JsonValue]:
    """Demote a project-scope guardrail memory level by one step."""
    memory_item = get_project_memory(project_id, memory_ref)
    try:
        memory_item.demote_project_guardrail_level(reason)
    except ValueError as exc:
        raise ValidationError(
            code="INVALID_MEMORY_DEMOTION",
            message="Memory demotion failed validation.",
            details={"reason": str(exc), "memory_ref": memory_item.id},
        ) from exc
    return memory_to_dict(memory_item)


def archive_memory(project_id: str, memory_ref: str) -> dict[str, JsonValue]:
    """Archive a memory via self-supersession so default discovery omits it."""
    memory_item = get_project_memory(project_id, memory_ref)
    if memory_item.superseded_by is not None:
        raise ValidationError(
            code="MEMORY_ALREADY_SUPERSEDED",
            message="Cannot archive a memory that is already superseded or archived.",
            details={"memory_ref": memory_item.id, "superseded_by": memory_item.superseded_by},
        )
    memory_item.update(superseded_by=memory_item.id)
    return memory_to_dict(memory_item)


def delete_memory(project_id: str, memory_ref: str, *, force: bool = False) -> dict[str, JsonValue]:
    """Delete a memory, preferring reversible lifecycle actions unless forced."""
    memory_item = get_project_memory(project_id, memory_ref)
    if not force and memory_item.superseded_by is None:
        raise ValidationError(
            code="MEMORY_DELETE_REQUIRES_FORCE",
            message="Delete is blocked for active memories; prefer supersede, archive, or demote.",
            details={
                "memory_ref": memory_item.id,
                "recommended_actions": ["supersede", "archive", "demote"],
            },
        )
    deleted_id = memory_item.id
    memory_item.delete()
    return {"id": deleted_id, "deleted": True}
