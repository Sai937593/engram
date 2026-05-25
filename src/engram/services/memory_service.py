"""Memory service read operations."""

from __future__ import annotations

from engram.models.memory import Memory
from engram.services.errors import EngramServiceError, JsonValue
from engram.services.serializers import memory_to_dict


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
    """Return project-scoped JSON-safe memory DTOs matching an FTS query."""
    validated_limit = _validate_limit(limit)
    matches = Memory.search(query, type_filter=type_filter, tag_filters=tags)

    project_matches = [
        memory_item for memory_item in matches if memory_item.project_id == project_id
    ]
    return [memory_to_dict(memory_item) for memory_item in project_matches[:validated_limit]]
