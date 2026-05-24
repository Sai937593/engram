"""Contracts shared by task-memory retrieval implementations."""

from __future__ import annotations

from dataclasses import dataclass

from engram.memory_retrieval.fts_query import MAX_FTS_TERM_CHARS, MAX_FTS_TERMS


@dataclass(frozen=True)
class TaskMemoryRetrievalOptions:
    """Deterministic knobs for task-memory FTS retrieval."""

    max_candidates: int = 20
    orchestration_timeout_seconds: float | None = 1.0
    max_query_terms: int = MAX_FTS_TERMS
    max_term_chars: int = MAX_FTS_TERM_CHARS
    task_id_match_boost: int = 3
    title_term_boost: int = 2
    tag_term_boost: int = 1


@dataclass(frozen=True)
class TaskMemoryCandidate:
    """Task-memory retrieval candidate with rank and debug details."""

    memory_id: str
    project_id: str
    scope: str
    type: str
    task_id: str | None
    title: str
    content: str
    tags: tuple[str, ...]
    retrieval_source: str
    fts_rank: float
    boost_score: int
    task_id_match: bool
    title_term_hits: tuple[str, ...]
    tag_term_hits: tuple[str, ...]


@dataclass(frozen=True)
class TaskMemoryRetrievalMetadata:
    """Metadata explaining the retrieval query and candidate set shape."""

    project_id: str
    query_task_id: str
    source: str
    requested_query_text: str
    normalized_fts_query: str
    query_term_count: int
    query_was_empty: bool
    fallback_used: bool
    fallback_reason: str | None
    max_candidates: int
    scanned_row_count: int
    returned_candidate_count: int


@dataclass(frozen=True)
class TaskMemoryRetrievalResult:
    """Result bundle for task-memory FTS retrieval."""

    candidates: tuple[TaskMemoryCandidate, ...]
    metadata: TaskMemoryRetrievalMetadata


@dataclass(frozen=True)
class RawMemoryRow:
    """Raw FTS row before deterministic boost and tie-break ordering."""

    memory_id: str
    project_id: str
    scope: str
    level: str | None
    type: str
    task_id: str | None
    title: str
    content: str
    tags: tuple[str, ...]
    fts_rank: float
