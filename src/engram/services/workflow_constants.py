"""Shared constants for workflow services."""

from __future__ import annotations

CONVENTIONAL_COMMIT_TYPES: set[str] = {
    "feat",
    "fix",
    "docs",
    "chore",
    "refactor",
    "test",
    "ci",
    "style",
    "perf",
}
