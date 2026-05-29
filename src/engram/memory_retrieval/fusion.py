"""Deterministic fusion of independent FTS and semantic retrieval candidates."""

from __future__ import annotations

from dataclasses import dataclass

from engram.memory_retrieval.retrieval_contract import (
    TaskMemoryCandidate,
    TaskMemoryRetrievalMetadata,
    TaskMemoryRetrievalResult,
)


@dataclass(frozen=True)
class _CandidateChannels:
    """Channel pair for one memory id during deterministic fusion."""

    fts: TaskMemoryCandidate | None = None
    semantic: TaskMemoryCandidate | None = None


def _is_exact_fts_candidate(candidate: TaskMemoryCandidate) -> bool:
    """Return whether an FTS candidate carries direct lexical/task-match signal."""

    return bool(
        candidate.task_id_match
        or candidate.title_term_hits
        or candidate.tag_term_hits
        or candidate.boost_score > 0
    )


def _resolve_semantic_status(metadata: TaskMemoryRetrievalMetadata) -> tuple[str, str | None]:
    """Resolve semantic index status label from semantic channel metadata."""

    if metadata.query_was_empty:
        return ("query-empty", None)
    if not metadata.fallback_used:
        return ("ready", None)
    reason = metadata.fallback_reason or ""
    if reason.startswith("semantic index "):
        # Expected shape: "semantic index <status>: <reason>".
        status_part = reason.split("semantic index ", maxsplit=1)[1].split(":", maxsplit=1)[0]
        return (status_part.strip() or "fallback", metadata.fallback_reason)
    return ("error", metadata.fallback_reason)


def _build_fused_candidate(
    *,
    channels: _CandidateChannels,
    memory_id: str,
) -> TaskMemoryCandidate:
    """Merge channel-specific candidate details into one deterministic candidate."""

    fts_candidate = channels.fts
    semantic_candidate = channels.semantic
    primary = fts_candidate or semantic_candidate
    if primary is None:
        raise ValueError(f"missing primary candidate for memory_id {memory_id}")

    exact_fts = bool(fts_candidate and _is_exact_fts_candidate(fts_candidate))

    if fts_candidate and semantic_candidate:
        retrieval_source = "fts+semantic"
    elif fts_candidate:
        retrieval_source = "fts"
    else:
        retrieval_source = "semantic"

    if exact_fts:
        fused_boost = max(2, fts_candidate.boost_score if fts_candidate else 0)
    elif semantic_candidate:
        fused_boost = max(1, fts_candidate.boost_score if fts_candidate else 0)
    else:
        fused_boost = fts_candidate.boost_score if fts_candidate else 0

    rank_source = fts_candidate or semantic_candidate

    return TaskMemoryCandidate(
        memory_id=primary.memory_id,
        project_id=primary.project_id,
        scope=primary.scope,
        type=primary.type,
        task_id=primary.task_id,
        title=primary.title,
        content=primary.content,
        tags=primary.tags,
        retrieval_source=retrieval_source,
        fts_rank=rank_source.fts_rank if rank_source else 0.0,
        boost_score=fused_boost,
        task_id_match=bool(
            (fts_candidate and fts_candidate.task_id_match) or primary.task_id_match
        ),
        title_term_hits=fts_candidate.title_term_hits if fts_candidate else primary.title_term_hits,
        tag_term_hits=fts_candidate.tag_term_hits if fts_candidate else primary.tag_term_hits,
        content_term_hits=(
            fts_candidate.content_term_hits if fts_candidate else primary.content_term_hits
        ),
    )


def fuse_task_memory_retrieval_results(
    *,
    fts_result: TaskMemoryRetrievalResult,
    semantic_result: TaskMemoryRetrievalResult,
    max_candidates: int,
) -> TaskMemoryRetrievalResult:
    """Fuse FTS and semantic candidate sets deterministically with source-aware metadata."""

    by_memory_id: dict[str, _CandidateChannels] = {}
    for candidate in fts_result.candidates:
        by_memory_id[candidate.memory_id] = _CandidateChannels(
            fts=candidate,
            semantic=by_memory_id.get(candidate.memory_id, _CandidateChannels()).semantic,
        )
    for candidate in semantic_result.candidates:
        by_memory_id[candidate.memory_id] = _CandidateChannels(
            fts=by_memory_id.get(candidate.memory_id, _CandidateChannels()).fts,
            semantic=candidate,
        )

    fused_candidates = tuple(
        sorted(
            (
                _build_fused_candidate(channels=channels, memory_id=memory_id)
                for memory_id, channels in by_memory_id.items()
            ),
            key=lambda candidate: (
                -candidate.boost_score,
                candidate.fts_rank,
                0 if candidate.retrieval_source in ("fts", "fts+semantic") else 1,
                candidate.memory_id,
            ),
        )[:max_candidates]
    )

    semantic_status, semantic_reason = _resolve_semantic_status(semantic_result.metadata)
    duplicate_count = sum(
        1
        for channels in by_memory_id.values()
        if channels.fts is not None and channels.semantic is not None
    )
    exact_fts_preserved_count = sum(
        1
        for candidate in fused_candidates
        if candidate.retrieval_source in ("fts", "fts+semantic")
        and _is_exact_fts_candidate(candidate)
    )

    fts_metadata = fts_result.metadata
    metadata = TaskMemoryRetrievalMetadata(
        project_id=fts_metadata.project_id,
        query_task_id=fts_metadata.query_task_id,
        source="semantic+fts",
        requested_query_text=fts_metadata.requested_query_text,
        normalized_fts_query=fts_metadata.normalized_fts_query,
        query_term_count=fts_metadata.query_term_count,
        query_was_empty=fts_metadata.query_was_empty,
        fallback_used=fts_metadata.fallback_used,
        fallback_reason=fts_metadata.fallback_reason,
        max_candidates=fts_metadata.max_candidates,
        scanned_row_count=fts_metadata.scanned_row_count,
        returned_candidate_count=len(fused_candidates),
        threshold_min_content_term_hits_without_title_or_tag=(
            fts_metadata.threshold_min_content_term_hits_without_title_or_tag
        ),
        threshold_filtered_row_count=fts_metadata.threshold_filtered_row_count,
        scanned_task_scope_row_count=fts_metadata.scanned_task_scope_row_count,
        scanned_project_scope_row_count=fts_metadata.scanned_project_scope_row_count,
        returned_task_scope_candidate_count=sum(
            1 for candidate in fused_candidates if candidate.scope == "task"
        ),
        returned_project_scope_candidate_count=sum(
            1 for candidate in fused_candidates if candidate.scope == "project"
        ),
        threshold_filtered_task_scope_count=fts_metadata.threshold_filtered_task_scope_count,
        threshold_filtered_project_scope_count=fts_metadata.threshold_filtered_project_scope_count,
        semantic_status=semantic_status,
        semantic_reason=semantic_reason,
        semantic_fallback_used=semantic_result.metadata.fallback_used,
        fts_returned_candidate_count=len(fts_result.candidates),
        semantic_returned_candidate_count=len(semantic_result.candidates),
        fused_duplicate_count=duplicate_count,
        exact_fts_preserved_count=exact_fts_preserved_count,
    )
    return TaskMemoryRetrievalResult(candidates=fused_candidates, metadata=metadata)
