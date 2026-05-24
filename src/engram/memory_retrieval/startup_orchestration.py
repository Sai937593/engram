"""Startup orchestration for task-memory retrieval pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from engram.memory_retrieval.fts_retriever import retrieve_task_memory_candidates
from engram.memory_retrieval.pack_contract import (
    TaskMemoryPackOptions,
    TaskMemoryPackResult,
    pack_task_memories,
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

    if not selected_task:
        empty_metadata = _build_empty_retrieval_metadata(
            project_id=project.id,
            query_task_id="",
            max_candidates=resolved_retrieval_options.max_candidates,
            source="none",
            fallback_used=False,
            fallback_reason=None,
        )
        empty_pack = pack_task_memories((), empty_metadata, pack_options)
        return StartupTaskMemoryRetrievalResult(
            query=None,
            retrieval_metadata=empty_metadata,
            pack_result=empty_pack,
        )

    retrieval_query = build_task_retrieval_query(
        selected_task,
        active_phase=active_phase,
        context=query_context,
        options=query_options,
    )

    try:
        retrieval_result = retrieve_task_memory_candidates(
            retrieval_query, resolved_retrieval_options
        )
        packed = pack_task_memories(
            retrieval_result.candidates,
            retrieval_result.metadata,
            pack_options,
        )
        return StartupTaskMemoryRetrievalResult(
            query=retrieval_query,
            retrieval_metadata=retrieval_result.metadata,
            pack_result=packed,
        )
    except Exception as exc:  # pragma: no cover - safety net for startup resilience
        fallback_metadata = TaskMemoryRetrievalMetadata(
            project_id=project.id,
            query_task_id=selected_task.id,
            source="fts",
            requested_query_text=retrieval_query.query_text,
            normalized_fts_query="",
            query_term_count=0,
            query_was_empty=False,
            fallback_used=True,
            fallback_reason=str(exc),
            max_candidates=resolved_retrieval_options.max_candidates,
            scanned_row_count=0,
            returned_candidate_count=0,
        )
        empty_pack = pack_task_memories((), fallback_metadata, pack_options)
        return StartupTaskMemoryRetrievalResult(
            query=retrieval_query,
            retrieval_metadata=fallback_metadata,
            pack_result=empty_pack,
        )
