"""Startup orchestration for task-memory retrieval pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from time import monotonic

from engram.memory_retrieval.fts_retriever import retrieve_task_memory_candidates
from engram.memory_retrieval.pack_contract import (
    TaskMemoryPackMetadata,
    TaskMemoryPackOptions,
    TaskMemoryPackResult,
    pack_task_memories,
    resolve_task_memory_pack_options,
)
from engram.memory_retrieval.query_builder import (
    RetrievalQueryBuilderOptions,
    TaskRetrievalQuery,
    build_task_retrieval_query,
)
from engram.memory_retrieval.retrieval_contract import (
    TaskMemoryRetrievalMetadata,
    TaskMemoryRetrievalOptions,
)
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task


@dataclass(frozen=True)
class StartupTaskMemoryRetrievalResult:
    """Result bundle for startup retrieval query, retrieval, and packed selection."""

    query: TaskRetrievalQuery | None
    retrieval_metadata: TaskMemoryRetrievalMetadata
    pack_result: TaskMemoryPackResult


def _build_empty_pack_result(
    retrieval_metadata: TaskMemoryRetrievalMetadata,
    pack_options: TaskMemoryPackOptions | None,
) -> TaskMemoryPackResult:
    """Build deterministic empty pack result without invoking pack logic."""

    resolved_pack_options = resolve_task_memory_pack_options(pack_options)
    metadata = TaskMemoryPackMetadata(
        project_id=retrieval_metadata.project_id,
        query_task_id=retrieval_metadata.query_task_id,
        source=retrieval_metadata.source,
        section_char_budget=resolved_pack_options.section_char_budget,
        preferred_k=resolved_pack_options.preferred_k,
        max_k=resolved_pack_options.max_k,
        max_item_chars=resolved_pack_options.max_item_chars,
        input_candidate_count=0,
        unique_candidate_count=0,
        selected_item_count=0,
        hidden_item_count=0,
        truncated_item_count=0,
        used_char_count=0,
        section_budget_exhausted=False,
        ordering_fields=resolved_pack_options.ordering_fields,
        dedupe_key=resolved_pack_options.dedupe_key,
    )
    return TaskMemoryPackResult(items=(), metadata=metadata)


def _build_empty_retrieval_metadata(
    *,
    project_id: str,
    query_task_id: str,
    max_candidates: int,
    source: str,
    fallback_used: bool,
    fallback_reason: str | None,
) -> TaskMemoryRetrievalMetadata:
    """Build deterministic empty retrieval metadata for skipped/fallback paths."""

    return TaskMemoryRetrievalMetadata(
        project_id=project_id,
        query_task_id=query_task_id,
        source=source,
        requested_query_text="",
        normalized_fts_query="",
        query_term_count=0,
        query_was_empty=True,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        max_candidates=max_candidates,
        scanned_row_count=0,
        returned_candidate_count=0,
    )


def _build_fallback_result(
    *,
    project: Project,
    selected_task: Task | None,
    retrieval_query: TaskRetrievalQuery | None,
    max_candidates: int,
    fallback_reason: str,
    source: str = "fts",
    pack_options: TaskMemoryPackOptions | None = None,
) -> StartupTaskMemoryRetrievalResult:
    """Return deterministic fallback metadata and empty pack result."""

    metadata = TaskMemoryRetrievalMetadata(
        project_id=project.id,
        query_task_id=selected_task.id if selected_task else "",
        source=source,
        requested_query_text=retrieval_query.query_text if retrieval_query else "",
        normalized_fts_query="",
        query_term_count=0,
        query_was_empty=retrieval_query is None,
        fallback_used=True,
        fallback_reason=fallback_reason,
        max_candidates=max_candidates,
        scanned_row_count=0,
        returned_candidate_count=0,
    )
    return StartupTaskMemoryRetrievalResult(
        query=retrieval_query,
        retrieval_metadata=metadata,
        pack_result=_build_empty_pack_result(metadata, pack_options),
    )


def _did_timeout(
    *,
    started_at: float,
    timeout_seconds: float | None,
) -> bool:
    """Return True when elapsed orchestration time crossed timeout."""

    return bool(
        timeout_seconds is not None
        and timeout_seconds > 0
        and (monotonic() - started_at) >= timeout_seconds
    )


def _timeout_reason(timeout_seconds: float, stage: str) -> str:
    """Return stable timeout reason text for fallback metadata."""

    return f"startup task-memory retrieval timed out after {timeout_seconds:.3f}s during {stage}"


def orchestrate_startup_task_memory_retrieval(
    *,
    project: Project,
    active_phase: Phase | None,
    selected_task: Task | None,
    query_context: Mapping[str, str | None] | None = None,
    query_options: RetrievalQueryBuilderOptions | None = None,
    retrieval_options: TaskMemoryRetrievalOptions | None = None,
    pack_options: TaskMemoryPackOptions | None = None,
) -> StartupTaskMemoryRetrievalResult:
    """Build query, retrieve candidates, and pack task memories for startup callers."""

    resolved_retrieval_options = retrieval_options or TaskMemoryRetrievalOptions()
    started_at = monotonic()

    if not selected_task:
        empty_metadata = _build_empty_retrieval_metadata(
            project_id=project.id,
            query_task_id="",
            max_candidates=resolved_retrieval_options.max_candidates,
            source="none",
            fallback_used=False,
            fallback_reason=None,
        )
        empty_pack = _build_empty_pack_result(empty_metadata, pack_options)
        return StartupTaskMemoryRetrievalResult(
            query=None,
            retrieval_metadata=empty_metadata,
            pack_result=empty_pack,
        )

    try:
        retrieval_query = build_task_retrieval_query(
            selected_task,
            active_phase=active_phase,
            context=query_context,
            options=query_options,
        )

        timeout_seconds = resolved_retrieval_options.orchestration_timeout_seconds
        if timeout_seconds is not None and _did_timeout(
            started_at=started_at,
            timeout_seconds=timeout_seconds,
        ):
            return _build_fallback_result(
                project=project,
                selected_task=selected_task,
                retrieval_query=retrieval_query,
                max_candidates=resolved_retrieval_options.max_candidates,
                fallback_reason=_timeout_reason(timeout_seconds, "query-build"),
                pack_options=pack_options,
            )

        retrieval_result = retrieve_task_memory_candidates(
            retrieval_query, resolved_retrieval_options
        )

        if timeout_seconds is not None and _did_timeout(
            started_at=started_at,
            timeout_seconds=timeout_seconds,
        ):
            return _build_fallback_result(
                project=project,
                selected_task=selected_task,
                retrieval_query=retrieval_query,
                max_candidates=resolved_retrieval_options.max_candidates,
                fallback_reason=_timeout_reason(timeout_seconds, "retrieval"),
                pack_options=pack_options,
            )

        packed = pack_task_memories(
            retrieval_result.candidates,
            retrieval_result.metadata,
            pack_options,
        )

        if timeout_seconds is not None and _did_timeout(
            started_at=started_at,
            timeout_seconds=timeout_seconds,
        ):
            return _build_fallback_result(
                project=project,
                selected_task=selected_task,
                retrieval_query=retrieval_query,
                max_candidates=resolved_retrieval_options.max_candidates,
                fallback_reason=_timeout_reason(timeout_seconds, "packing"),
                pack_options=pack_options,
            )

        return StartupTaskMemoryRetrievalResult(
            query=retrieval_query,
            retrieval_metadata=retrieval_result.metadata,
            pack_result=packed,
        )
    except Exception as exc:  # pragma: no cover - safety net for startup resilience
        return _build_fallback_result(
            project=project,
            selected_task=selected_task,
            retrieval_query=locals().get("retrieval_query"),
            max_candidates=resolved_retrieval_options.max_candidates,
            fallback_reason=str(exc),
            pack_options=pack_options,
        )
