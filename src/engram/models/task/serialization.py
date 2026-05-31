"""Task serialization and path normalization helpers."""

import json
from typing import Any


def normalize_relevant_files(relevant_files: Any) -> list[str]:
    """Normalize relevant file paths by trimming entries, dropping empties, and deduplicating."""
    if relevant_files is None:
        return []
    if isinstance(relevant_files, str):
        candidates = [relevant_files]
    else:
        candidates = list(relevant_files)

    normalized: list[str] = []
    seen: set[str] = set()
    for path in candidates:
        if path is None:
            continue
        cleaned = str(path).strip()
        if cleaned and cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)
    return normalized


def serialize_relevant_files(relevant_files: list[str]) -> str:
    """Serialize relevant files for database storage."""
    return json.dumps(relevant_files)


def deserialize_relevant_files(value: Any) -> list[str]:
    """Deserialize relevant file path metadata from DB values."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return normalize_relevant_files(value.split(","))
        return normalize_relevant_files(loaded)
    return normalize_relevant_files(value)
