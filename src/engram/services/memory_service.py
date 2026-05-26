"""Memory service read operations."""

from __future__ import annotations

from engram.models.memory import Memory
from engram.services.errors import EngramServiceError, JsonValue, ValidationError
from engram.services.serializers import memory_to_dict

VALID_MEMORY_TYPES = {"note", "lesson", "decision", "constraint", "snippet"}


def _validate_limit(limit: int) -> int:
    """Validate memory query limits for service-layer read APIs."""
    if limit <= 0:
        raise EngramServiceError(
            code="VALIDATION_ERROR",
            message="Limit must be a positive integer.",
            details={"field": "limit", "value": limit},
        )
    return limit


def search_memories(
    project_id: str,
    query: str | None,
    type_filter: str | None = None,
    tags: list[str] | tuple[str, ...] | None = None,
    limit: int = 10,
) -> list[dict[str, JsonValue]]:
    """Return project-scoped JSON-safe memory DTOs matching an FTS query or list fallback."""
    validated_limit = _validate_limit(limit)

    # Check if query actually has signal terms. If not, use list fallback.
    from engram.memory_retrieval.fts_query import _extract_search_terms

    terms = _extract_search_terms(query)

    if not terms:
        # Fallback to listing memories
        memories = list_memories(project_id, type_filter=type_filter)
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
    matches = Memory.search(query, type_filter=type_filter, tag_filters=tags, project_id=project_id)

    return [memory_to_dict(memory_item) for memory_item in matches[:validated_limit]]


def list_memories(
    project_id: str,
    type_filter: str | None = None,
    limit: int | None = None,
) -> list[dict[str, JsonValue]]:
    """Return project-scoped JSON-safe memory DTOs using list model behavior."""
    if type_filter:
        memories = Memory.list_by_type(project_id, type_filter)
    else:
        memories = Memory.list_by_project(project_id)

    if limit is None:
        return [memory_to_dict(memory_item) for memory_item in memories]

    validated_limit = _validate_limit(limit)
    return [memory_to_dict(memory_item) for memory_item in memories[:validated_limit]]


def create_memory(
    project_id: str,
    type: str,
    title: str,
    content: str,
    scope: str = "project",
    task_id: str | None = None,
    tags: list[str] | None = None,
    always_include: bool = False,
    level: str | None = None,
    id: str | None = None,
) -> dict[str, JsonValue]:
    """Create a new memory with validation and return its JSON-safe DTO."""
    if type not in VALID_MEMORY_TYPES:
        raise ValidationError(
            code="INVALID_MEMORY_TYPE",
            message="Memory type is invalid.",
            details={"type": type, "allowed_types": sorted(list(VALID_MEMORY_TYPES))},
        )

    if scope not in {"project", "task"}:
        raise ValidationError(
            code="INVALID_MEMORY_SCOPE",
            message="Memory scope is invalid.",
            details={"scope": scope, "allowed_scopes": ["project", "task"]},
        )

    normalized_level = level.strip() if level else None
    if scope == "project":
        if not normalized_level or normalized_level not in {"L0", "L1", "L2", "L3"}:
            raise ValidationError(
                code="INVALID_MEMORY_LEVEL",
                message="Project-scope memories require a valid level (L0, L1, L2, or L3).",
                details={"level": level, "allowed_levels": ["L0", "L1", "L2", "L3"]},
            )
    elif scope == "task":
        if normalized_level is not None:
            raise ValidationError(
                code="INVALID_MEMORY_LEVEL",
                message="Task-scope memories must not define a level.",
                details={"level": level},
            )

    memory_item = Memory.create(
        project_id=project_id,
        type=type,
        title=title,
        content=content,
        scope=scope,
        task_id=task_id,
        tags=tags,
        always_include=always_include,
        level=normalized_level,
        id=id,
    )
    return memory_to_dict(memory_item)
