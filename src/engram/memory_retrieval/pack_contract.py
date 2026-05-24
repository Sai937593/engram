"""Contracts for deterministic task-memory selection and budgeted packing."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_TASK_MEMORY_PACK_ORDERING = ("-boost_score", "fts_rank", "memory_id")


@dataclass(frozen=True)
class TaskMemoryPackOptions:
    """Deterministic limits used when packing retrieval candidates for startup."""

    section_char_budget: int = 3600
    preferred_k: int = 6
    max_k: int = 10
    max_item_chars: int = 420
    ordering_fields: tuple[str, ...] = DEFAULT_TASK_MEMORY_PACK_ORDERING
    dedupe_key: str = "memory_id"


@dataclass(frozen=True)
class TaskMemoryPackedItem:
    """One packed task-memory item selected from retrieval candidates."""

    memory_id: str
    type: str
    title: str
    content: str
    tags: tuple[str, ...]
    task_id: str | None
    retrieval_source: str
    fts_rank: float
    boost_score: int
    source_candidate_index: int
    char_count: int
    was_truncated: bool


@dataclass(frozen=True)
class TaskMemoryPackMetadata:
    """Pack-level metadata for deterministic debug output and test assertions."""

    project_id: str
    query_task_id: str
    source: str
    section_char_budget: int
    preferred_k: int
    max_k: int
    max_item_chars: int
    input_candidate_count: int
    unique_candidate_count: int
    selected_item_count: int
    hidden_item_count: int
    truncated_item_count: int
    used_char_count: int
    section_budget_exhausted: bool
    ordering_fields: tuple[str, ...]
    dedupe_key: str


@dataclass(frozen=True)
class TaskMemoryPackResult:
    """Packed items plus metadata for startup rendering and retrieval debug."""

    items: tuple[TaskMemoryPackedItem, ...]
    metadata: TaskMemoryPackMetadata


def resolve_task_memory_pack_options(
    options: TaskMemoryPackOptions | None,
) -> TaskMemoryPackOptions:
    """Return explicit pack options or deterministic defaults."""

    return options or TaskMemoryPackOptions()
