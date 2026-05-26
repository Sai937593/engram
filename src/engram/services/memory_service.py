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

    matches = Memory.search(query, type_filter=type_filter, tag_filters=tags)

    project_matches = [
        memory_item for memory_item in matches if memory_item.project_id == project_id
    ]
    return [memory_to_dict(memory_item) for memory_item in project_matches[:validated_limit]]


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
