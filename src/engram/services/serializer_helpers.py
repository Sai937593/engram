"""Shared helper functions for service serializers."""

from __future__ import annotations

from typing import Any

from engram.models.task import Task


def none_if_blank(value: Any) -> str | None:
    """Return None for missing or blank string values."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def string_list(value: Any) -> list[str]:
    """Normalize list-like values into a JSON-safe list of strings."""
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        source = value
    else:
        source = [value]

    normalized: list[str] = []
    for item in source:
        if item is None:
            continue
        cleaned = str(item).strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def get_effective_status(task: Task) -> str:
    """Compute dependency-aware status without importing CLI helpers."""
    status = task.status
    if status in {"draft", "ready", "todo"}:
        status = "open"
    elif status == "in-progress":
        status = "in_progress"

    if status in {"done", "cancelled"}:
        return status

    visited: set[str] = set()
    current = task
    has_unfinished = False
    has_blocked = False

    while current.depends_on:
        dep_id = current.depends_on
        if dep_id in visited:
            break
        visited.add(dep_id)

        dependency = Task.get(dep_id)
        if not dependency:
            break
        dep_status = dependency.status
        if dep_status in {"draft", "ready", "todo"}:
            dep_status = "open"
        elif dep_status == "in-progress":
            dep_status = "in_progress"

        if dep_status == "cancelled":
            return "cancelled"
        if dep_status == "blocked":
            has_blocked = True
        elif dep_status != "done":
            has_unfinished = True
        current = dependency

    if has_blocked or has_unfinished:
        return "blocked"
    return status
