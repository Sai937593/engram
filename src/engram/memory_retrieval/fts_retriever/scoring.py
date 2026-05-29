"""Boost and scoring logic for task memory retrieval."""

from __future__ import annotations

import re as _re
from math import sqrt as _sqrt
from typing import Any as _Any

from engram.memory_retrieval.retrieval_contract import (
    TaskMemoryRetrievalMetadata as _TaskMemoryRetrievalMetadata,
)

_PROJECT_SCOPE_ELIGIBLE_LEVELS = ("L2", "L3")
_PROJECT_SCOPE_ELIGIBLE_TYPES = ("lesson", "decision")
_TOKEN_PATTERN = _re.compile(r"\w+", flags=_re.UNICODE)


def _extract_token_set(text: str | None) -> set[str]:
    """Extract casefolded lexical tokens from text for deterministic hit checks."""
    if not text:
        return set()
    return {token.casefold() for token in _TOKEN_PATTERN.findall(text)}


def _passes_lexical_threshold(
    *,
    has_task_id_match: bool,
    title_hits: tuple[str, ...],
    tag_hits: tuple[str, ...],
    content_hits: tuple[str, ...],
    min_content_term_hits_without_title_or_tag: int,
) -> bool:
    """Return whether candidate signal is strong enough for deterministic inclusion."""
    if has_task_id_match or title_hits or tag_hits:
        return True
    if min_content_term_hits_without_title_or_tag <= 0:
        return True
    return len(content_hits) >= min_content_term_hits_without_title_or_tag


def _is_semantic_eligible(memory: _Any) -> bool:
    """Return whether memory is eligible for semantic retrieval candidates."""
    if getattr(memory, "superseded_by", None) is not None:
        return False
    if memory.scope == "task":
        return True
    if memory.scope != "project":
        return False
    return bool(
        memory.level in _PROJECT_SCOPE_ELIGIBLE_LEVELS
        and memory.type in _PROJECT_SCOPE_ELIGIBLE_TYPES
    )


def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    """Compute cosine similarity for vectors with equal dimensionality."""
    if not left or not right or len(left) != len(right):
        return 0.0
    left_norm = _sqrt(sum(value * value for value in left))
    right_norm = _sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    dot = sum(left[index] * right[index] for index in range(len(left)))
    return dot / (left_norm * right_norm)


def compute_boost_score(
    has_task_id_match: bool,
    title_hits: tuple[str, ...],
    tag_hits: tuple[str, ...],
    options: _Any,
) -> float:
    """Compute the boost score for a candidate based on search term hits."""
    return (
        (options.task_id_match_boost if has_task_id_match else 0)
        + (options.title_term_boost if title_hits else 0)
        + (options.tag_term_boost if tag_hits else 0)
    )


def build_retrieval_metadata(
    **kwargs: _Any,
) -> _TaskMemoryRetrievalMetadata:
    """Build TaskMemoryRetrievalMetadata using kwargs helper."""
    return _TaskMemoryRetrievalMetadata(**kwargs)


def build_fts_meta(
    project_id: str,
    query_task_id: str,
    query_text: str,
    safe_fts_query: str,
    query_terms: tuple[str, ...],
    resolved_options: _Any,
    fts_rows: list[_Any],
    ordered_candidates: tuple[_Any, ...],
    filtered: int,
    scanned_task: int,
    scanned_project: int,
    filtered_task: int,
    filtered_project: int,
) -> _TaskMemoryRetrievalMetadata:
    """Build FTS retrieval metadata by calculating stats."""
    return build_retrieval_metadata(
        project_id=project_id,
        query_task_id=query_task_id,
        source="fts",
        requested_query_text=query_text,
        normalized_fts_query=safe_fts_query,
        query_term_count=len(query_terms),
        query_was_empty=False,
        fallback_used=False,
        fallback_reason=None,
        max_candidates=resolved_options.max_candidates,
        scanned_row_count=len(fts_rows),
        returned_candidate_count=len(ordered_candidates),
        threshold_min_content_term_hits_without_title_or_tag=(
            resolved_options.min_content_term_hits_without_title_or_tag
        ),
        threshold_filtered_row_count=filtered,
        scanned_task_scope_row_count=scanned_task,
        scanned_project_scope_row_count=scanned_project,
        returned_task_scope_candidate_count=sum(1 for c in ordered_candidates if c.scope == "task"),
        returned_project_scope_candidate_count=sum(
            1 for c in ordered_candidates if c.scope == "project"
        ),
        threshold_filtered_task_scope_count=filtered_task,
        threshold_filtered_project_scope_count=filtered_project,
    )


def build_empty_fts_meta(
    project_id: str,
    query_task_id: str,
    query_text: str,
    safe_fts_query: str,
    query_terms: tuple[str, ...],
    resolved_options: _Any,
    query_was_empty: bool = False,
    fallback_used: bool = False,
    fallback_reason: str | None = None,
) -> _TaskMemoryRetrievalMetadata:
    """Build empty FTS retrieval metadata with defaults."""
    return build_retrieval_metadata(
        project_id=project_id,
        query_task_id=query_task_id,
        source="fts",
        requested_query_text=query_text,
        normalized_fts_query=safe_fts_query,
        query_term_count=len(query_terms),
        query_was_empty=query_was_empty,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        max_candidates=resolved_options.max_candidates,
        scanned_row_count=0,
        returned_candidate_count=0,
        threshold_min_content_term_hits_without_title_or_tag=(
            resolved_options.min_content_term_hits_without_title_or_tag
        ),
        threshold_filtered_row_count=0,
        scanned_task_scope_row_count=0,
        scanned_project_scope_row_count=0,
        returned_task_scope_candidate_count=0,
        returned_project_scope_candidate_count=0,
        threshold_filtered_task_scope_count=0,
        threshold_filtered_project_scope_count=0,
    )
