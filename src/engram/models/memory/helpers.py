from typing import Any

from engram.db import get_db_connection
from engram.models.audit import AuditLog

VALID_MEMORY_SCOPES = {"project", "task"}
VALID_PROJECT_LEVELS = {"L0", "L1", "L2", "L3"}
GUARDRAIL_DEMOTION_LEVEL_MAP = {"L0": "L1", "L1": "L2", "L2": "L3"}


def _normalize_level(level: str | None) -> str | None:
    if level is None:
        return None
    normalized_level = level.strip()
    if not normalized_level:
        return None
    return normalized_level


def _validate_scope_level(scope: str, level: str | None) -> str | None:
    if scope not in VALID_MEMORY_SCOPES:
        raise ValueError(
            f"Invalid memory scope '{scope}'. Allowed values: {', '.join(sorted(VALID_MEMORY_SCOPES))}."
        )

    normalized_level = _normalize_level(level)
    if normalized_level is not None and normalized_level not in VALID_PROJECT_LEVELS:
        raise ValueError(
            f"Invalid memory level '{normalized_level}'. Allowed values: {', '.join(sorted(VALID_PROJECT_LEVELS))}."
        )

    if scope == "project" and normalized_level is None:
        raise ValueError("Project-scope memories require a valid level (L0, L1, L2, or L3).")
    if scope == "task" and normalized_level is not None:
        raise ValueError("Task-scope memories must not define a level.")

    return normalized_level


def demote_project_guardrail_level(memory: Any, reason: str) -> tuple[str, str]:
    """Demote a project-scope guardrail level by exactly one level and audit the reason."""
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise ValueError("Demotion reason cannot be empty.")

    if memory.scope != "project":
        raise ValueError(
            f"Memory '{memory.id}' is scope '{memory.scope}'. Only project-scope memories can be demoted."
        )

    current_level = _normalize_level(memory.level)
    if current_level is None or current_level not in VALID_PROJECT_LEVELS:
        raise ValueError(
            f"Memory '{memory.id}' has invalid level '{memory.level}'. Expected one of: L0, L1, L2, L3."
        )
    if current_level == "L3":
        raise ValueError(f"Memory '{memory.id}' is already at the lowest level (L3).")

    next_level = GUARDRAIL_DEMOTION_LEVEL_MAP[current_level]

    conn = get_db_connection()
    conn.execute(
        "UPDATE memories SET level = ?, updated_at = datetime('now') WHERE id = ?",
        (next_level, memory.id),
    )
    conn.commit()
    conn.close()

    memory.level = next_level
    AuditLog.log(
        "memories",
        memory.id,
        "guardrail_demote",
        field="level",
        old_value=current_level,
        new_value=next_level,
    )
    AuditLog.log(
        "memories",
        memory.id,
        "guardrail_demote",
        field="reason",
        old_value=None,
        new_value=normalized_reason,
    )

    return current_level, next_level


def update_memory_record(memory: Any, **kwargs) -> None:
    """Update a memory instance and database record with auditing."""
    next_scope = kwargs.get("scope", memory.scope)
    next_level = kwargs.get("level", memory.level)
    normalized_level = _validate_scope_level(scope=next_scope, level=next_level)
    if "level" in kwargs:
        kwargs["level"] = normalized_level

    updates = []
    params = []

    for key, value in kwargs.items():
        if hasattr(memory, key):
            old_value = getattr(memory, key)
            if old_value != value:
                updates.append(f"{key} = ?")
                if key == "tags":
                    params.append(",".join(value))
                elif key == "always_include":
                    params.append(1 if value else 0)
                else:
                    params.append(value)

                setattr(memory, key, value)
                AuditLog.log(
                    "memories",
                    memory.id,
                    "update",
                    field=key,
                    old_value=str(old_value),
                    new_value=str(value),
                )

    if not updates:
        return

    updates.append("updated_at = datetime('now')")
    params.append(memory.id)

    query = f"UPDATE memories SET {', '.join(updates)} WHERE id = ?"
    conn = get_db_connection()
    conn.execute(query, params)
    conn.commit()
    conn.close()
