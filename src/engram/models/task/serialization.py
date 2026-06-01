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


def normalize_search_hints(search_hints: Any) -> list[str]:
    """Normalize search hints by trimming entries, dropping empties, and deduplicating."""
    if search_hints is None:
        return []
    if isinstance(search_hints, str):
        candidates = [search_hints]
    else:
        candidates = list(search_hints)

    normalized: list[str] = []
    seen: set[str] = set()
    for hint in candidates:
        if hint is None:
            continue
        cleaned = str(hint).strip()
        if cleaned and cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)
    return normalized


def serialize_search_hints(search_hints: list[str]) -> str:
    """Serialize search hints for database storage."""
    return json.dumps(search_hints)


def deserialize_search_hints(value: Any) -> list[str]:
    """Deserialize search hints from DB values."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return normalize_search_hints(value.split(","))
        return normalize_search_hints(loaded)
    return normalize_search_hints(value)
