"""Validation and resolution helpers for memory service updates."""

from __future__ import annotations

from engram.models.memory import Memory
from engram.services.errors import EngramServiceError, JsonValue, ValidationError

VALID_MEMORY_TYPES = {"note", "lesson", "decision", "constraint", "snippet"}
DEFAULT_MEMORY_TYPE = "note"
DEFAULT_MEMORY_SCOPE = "project"
DEFAULT_PROJECT_LEVEL = "L3"
VALID_MEMORY_UPDATE_FIELDS = {
    "type",
    "title",
    "content",
    "scope",
    "task_id",
    "tags",
    "always_include",
    "level",
    "superseded_by",
}


def get_project_memory(project_id: str, memory_ref: str) -> Memory:
    """Resolve a memory reference and enforce project scoping."""
    candidate = memory_ref.strip()
    if not candidate:
        raise ValidationError(
            code="INVALID_MEMORY_REFERENCE",
            message="Memory reference cannot be empty.",
            details={"memory_ref": memory_ref},
        )
    memory_item = Memory.get(candidate)
    if memory_item is None or memory_item.project_id != project_id:
        raise EngramServiceError(
            code="MEMORY_NOT_FOUND",
            message="Memory reference was not found in this project.",
            details={"project_id": project_id, "memory_ref": candidate},
        )
    return memory_item


def validate_memory_updates(updates: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Validate update payload shape and writable fields."""
    if not updates:
        raise ValidationError(
            code="INVALID_MEMORY_UPDATE",
            message="Memory update requires at least one writable field.",
            details={"allowed_fields": sorted(VALID_MEMORY_UPDATE_FIELDS)},
        )
    unknown_fields = sorted(set(updates) - VALID_MEMORY_UPDATE_FIELDS)
    if unknown_fields:
        raise ValidationError(
            code="INVALID_MEMORY_UPDATE_FIELD",
            message="Memory update included unsupported field(s).",
            details={
                "fields": unknown_fields,
                "allowed_fields": sorted(VALID_MEMORY_UPDATE_FIELDS),
            },
        )
    if "type" in updates and str(updates["type"]) not in VALID_MEMORY_TYPES:
        raise ValidationError(
            code="INVALID_MEMORY_TYPE",
            message="Memory type is invalid.",
            details={"type": updates["type"], "allowed_types": sorted(list(VALID_MEMORY_TYPES))},
        )
    scope = str(updates["scope"]) if "scope" in updates else None
    if scope is not None and scope not in {"project", "task"}:
        raise ValidationError(
            code="INVALID_MEMORY_SCOPE",
            message="Memory scope is invalid.",
            details={"scope": updates["scope"], "allowed_scopes": ["project", "task"]},
        )
    return updates


def normalize_memory_create_payload(
    *,
    content: str,
    title: str | None,
    type: str | None,
    scope: str | None,
    level: str | None,
) -> tuple[str, str, str, str | None]:
    """Apply deterministic defaults for simplified memory creation."""
    normalized_content = content.strip()
    if not normalized_content:
        raise ValidationError(
            code="INVALID_MEMORY_CONTENT",
            message="Memory content cannot be empty.",
            details={"field": "content"},
        )
    normalized_title = (title or "").strip() or _derive_title_from_content(normalized_content)
    normalized_type = (type or DEFAULT_MEMORY_TYPE).strip()
    normalized_scope = (scope or DEFAULT_MEMORY_SCOPE).strip()
    normalized_level = level.strip() if isinstance(level, str) and level.strip() else None
    if normalized_scope == "project" and normalized_level is None:
        normalized_level = DEFAULT_PROJECT_LEVEL
    return normalized_type, normalized_title, normalized_scope, normalized_level


def _derive_title_from_content(content: str) -> str:
    preview = " ".join(content.split())
    if len(preview) <= 60:
        return preview
    return f"{preview[:57].rstrip()}..."
