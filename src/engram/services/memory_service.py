"""Memory service read operations."""

from __future__ import annotations

from engram.db import get_db_connection
from engram.models.memory import Memory
from engram.services.errors import EngramServiceError, JsonValue, ValidationError
from engram.services.memory_update_support import (
    DEFAULT_MEMORY_SCOPE,
    DEFAULT_MEMORY_TYPE,
    VALID_MEMORY_TYPES,
    get_project_memory,
    normalize_memory_create_payload,
    resolve_batch_memory_updates,
    validate_memory_updates,
)
from engram.services.serializers import compact_memory_to_dict, memory_to_dict


def _validate_limit(limit: int) -> int:
    """Validate memory query limits for service-layer read APIs."""
    if limit <= 0:
        raise EngramServiceError(
            code="VALIDATION_ERROR",
            message="Limit must be a positive integer.",
            details={"field": "limit", "value": limit},
        )
    return limit


def get_recent_memories(limit: int = 50, project_id: str | None = None) -> list[Memory]:
    """Return a list of recent memories. Limits up to 1000 items."""
    validated_limit = _validate_limit(limit)
    if validated_limit > 1000:
        validated_limit = 1000
    conn = get_db_connection()
    cursor = conn.cursor()

    if project_id:
        cursor.execute(
            "SELECT * FROM memories WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
            (project_id, validated_limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
            (validated_limit,),
        )

    rows = cursor.fetchall()
    conn.close()

    return [Memory.from_row(row) for row in rows]


def search_memories(
    project_id: str,
    query: str | None,
    type_filter: str | None = None,
    tags: list[str] | tuple[str, ...] | None = None,
    limit: int = 10,
    include_superseded: bool = False,
) -> list[dict[str, JsonValue]]:
    """Return project-scoped JSON-safe memory DTOs matching an FTS query or list fallback."""
    validated_limit = _validate_limit(limit)

    # Check if query actually has signal terms. If not, use list fallback.
    from engram.memory_retrieval.fts_query import _extract_search_terms

    terms = _extract_search_terms(query)

    if not terms:
        # Fallback to listing memories
        memories = list_memories(
            project_id,
            type_filter=type_filter,
            include_superseded=include_superseded,
            compact=False,
        )
        if tags:
            # Filter by tags manually in Python
            filtered = []
            for m in memories:
                # tags DTO is a list
                m_tags = m.get("tags") or []
                if all(any(tag.lower() in mt.lower() for mt in m_tags) for tag in tags):
                    filtered.append(m)
            memories = filtered
        return memories[:validated_limit]

    # Optimization: Filter by project_id in the database instead of in-memory.
    matches = Memory.search(
        query,
        type_filter=type_filter,
        tag_filters=tags,
        project_id=project_id,
        include_superseded=include_superseded,
    )

    return [memory_to_dict(memory_item) for memory_item in matches[:validated_limit]]


def list_memories(
    project_id: str,
    type_filter: str | None = None,
    limit: int | None = None,
    include_superseded: bool = False,
    compact: bool = True,
) -> list[dict[str, JsonValue]]:
    """Return project-scoped JSON-safe memory DTOs using list model behavior."""
    if type_filter:
        memories = Memory.list_by_type(
            project_id, type_filter, include_superseded=include_superseded
        )
    else:
        memories = Memory.list_by_project(project_id, include_superseded=include_superseded)

    if limit is None:
        return [_serialize_memory(memory_item, compact=compact) for memory_item in memories]

    validated_limit = _validate_limit(limit)
    return [
        _serialize_memory(memory_item, compact=compact)
        for memory_item in memories[:validated_limit]
    ]


def create_memory(
    project_id: str,
    content: str,
    title: str | None = None,
    type: str = DEFAULT_MEMORY_TYPE,
    scope: str = DEFAULT_MEMORY_SCOPE,
    level: str | None = None,
    task_id: str | None = None,
    tags: list[str] | None = None,
    always_include: bool = False,
    id: str | None = None,
    supersedes: str | None = None,
) -> dict[str, JsonValue]:
    """Create a new memory with defaults and return its JSON-safe DTO."""
    normalized_type, normalized_title, normalized_scope, normalized_level = (
        normalize_memory_create_payload(
            content=content,
            title=title,
            type=type,
            scope=scope,
            level=level,
        )
    )

    if normalized_type not in VALID_MEMORY_TYPES:
        raise ValidationError(
            code="INVALID_MEMORY_TYPE",
            message="Memory type is invalid.",
            details={"type": normalized_type, "allowed_types": sorted(list(VALID_MEMORY_TYPES))},
        )

    if normalized_scope not in {"project", "task"}:
        raise ValidationError(
            code="INVALID_MEMORY_SCOPE",
            message="Memory scope is invalid.",
            details={"scope": normalized_scope, "allowed_scopes": ["project", "task"]},
        )

    try:
        memory_item = Memory.create(
            project_id=project_id,
            type=normalized_type,
            title=normalized_title,
            content=content.strip(),
            scope=normalized_scope,
            task_id=task_id,
            tags=tags,
            always_include=always_include,
            level=normalized_level,
            id=id,
            supersedes=supersedes,
        )
    except ValueError as exc:
        raise ValidationError(
            code="INVALID_MEMORY_LEVEL",
            message="Memory creation failed validation.",
            details={"reason": str(exc)},
        ) from exc
    return memory_to_dict(memory_item)


def get_memory(project_id: str, memory_ref: str, compact: bool = True) -> dict[str, JsonValue]:
    """Resolve a project-scoped memory reference and return a JSON-safe DTO."""
    memory_item = get_project_memory(project_id, memory_ref)
    return _serialize_memory(memory_item, compact=compact)


def update_memory(project_id: str, memory_ref: str, **updates: JsonValue) -> dict[str, JsonValue]:
    """Update writable memory fields and return the updated JSON-safe DTO."""
    memory_item = get_project_memory(project_id, memory_ref)
    resolved = validate_memory_updates(updates)
    try:
        memory_item.update(**resolved)
    except ValueError as exc:
        raise ValidationError(
            code="INVALID_MEMORY_UPDATE",
            message="Memory update failed validation.",
            details={"reason": str(exc)},
        ) from exc
    return memory_to_dict(memory_item)


def update_memories(project_id: str, entries: list[dict[str, JsonValue]]) -> dict[str, JsonValue]:
    """Update multiple memories atomically and return a concise update summary."""
    resolved_entries = resolve_batch_memory_updates(project_id, entries)
    conn = get_db_connection()
    try:
        conn.execute("BEGIN")
        for memory_item, resolved_updates in resolved_entries:
            try:
                memory_item.update(conn=conn, **resolved_updates)
            except ValueError as exc:
                raise ValidationError(
                    code="INVALID_MEMORY_UPDATE",
                    message="Memory update failed validation.",
                    details={"reason": str(exc), "memory_ref": memory_item.id},
                ) from exc
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    updated_ids = [memory_item.id for memory_item, _ in resolved_entries]
    return {"updated_count": len(updated_ids), "updated_ids": updated_ids}


def _serialize_memory(memory_item: Memory, *, compact: bool) -> dict[str, JsonValue]:
    if not compact:
        return memory_to_dict(memory_item)
    conn = get_db_connection()
    row = conn.execute(
        "SELECT created_at, updated_at FROM memories WHERE id = ?",
        (memory_item.id,),
    ).fetchone()
    conn.close()
    created_at = None if row is None else row["created_at"]
    updated_at = None if row is None else row["updated_at"]
    return compact_memory_to_dict(memory_item, created_at=created_at, updated_at=updated_at)
