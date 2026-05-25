"""FTS retrieval over task memories and eligible project guidance candidates."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable
from math import sqrt
from typing import Any

from engram.db import get_db_connection
from engram.memory_retrieval.fts_query import (
    EMPTY_FTS_QUERY,
    normalize_fts_query_text,
)
from engram.memory_retrieval.query_builder import TaskRetrievalQuery
from engram.memory_retrieval.retrieval_contract import (
    RawMemoryRow,
    TaskMemoryCandidate,
    TaskMemoryRetrievalMetadata,
    TaskMemoryRetrievalOptions,
    TaskMemoryRetrievalResult,
)
from engram.memory_retrieval.semantic_index_contract import (
    DEFAULT_SEMANTIC_MODEL_NAME,
    SemanticIndexStatus,
    load_semantic_embedding_dependencies,
)
from engram.memory_retrieval.semantic_index_storage import SemanticIndexStorage

PROJECT_SCOPE_ELIGIBLE_LEVELS = ("L2", "L3")
PROJECT_SCOPE_ELIGIBLE_TYPES = ("lesson", "decision")
_TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)


def _split_csv_tags(raw_tags: str | None) -> tuple[str, ...]:
    """Convert CSV tag storage to deterministic trimmed tuple order."""
    if not raw_tags:
        return ()
    return tuple(tag.strip() for tag in raw_tags.split(",") if tag.strip())


def _extract_terms_from_safe_query(safe_query: str) -> tuple[str, ...]:
    """Extract quoted terms from a normalized FTS query string."""
    if safe_query == EMPTY_FTS_QUERY:
        return ()
    return tuple(
        token[1:-1].casefold()
        for token in safe_query.split(" OR ")
        if len(token) >= 2 and token.startswith('"') and token.endswith('"')
    )


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


def _is_semantic_eligible(memory: Any) -> bool:
    """Return whether memory is eligible for semantic retrieval candidates."""
    if memory.scope == "task":
        return True
    if memory.scope != "project":
        return False
    return bool(
        memory.level in PROJECT_SCOPE_ELIGIBLE_LEVELS
        and memory.type in PROJECT_SCOPE_ELIGIBLE_TYPES
    )


def _to_float_tuple(vector: Iterable[object]) -> tuple[float, ...]:
    """Convert numeric iterables to deterministic float tuples."""
    return tuple(float(value) for value in vector)


def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    """Compute cosine similarity for vectors with equal dimensionality."""
    if not left or not right or len(left) != len(right):
        return 0.0
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    dot = sum(left[index] * right[index] for index in range(len(left)))
    return dot / (left_norm * right_norm)


def _list_project_memories(project_id: str) -> list[Any]:
    """List project memories via local import to avoid package import cycles."""
    from engram.models.memory import Memory

    return Memory.list_by_project(project_id)


def _empty_semantic_result(
    *,
    project_id: str,
    task_id: str,
    query_text: str,
    max_candidates: int,
    query_was_empty: bool,
    fallback_used: bool,
    fallback_reason: str | None,
) -> TaskMemoryRetrievalResult:
    """Return deterministic empty semantic retrieval metadata."""
    metadata = TaskMemoryRetrievalMetadata(
        project_id=project_id,
        query_task_id=task_id,
        source="semantic",
        requested_query_text=query_text,
        normalized_fts_query="",
        query_term_count=0,
        query_was_empty=query_was_empty,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        max_candidates=max_candidates,
        scanned_row_count=0,
        returned_candidate_count=0,
    )
    return TaskMemoryRetrievalResult(candidates=(), metadata=metadata)


def _semantic_candidate_from_memory(
    *,
    memory: Any,
    similarity: float,
    query_task_id: str,
) -> TaskMemoryCandidate:
    """Build semantic retrieval candidate using similarity score as sortable rank."""
    return TaskMemoryCandidate(
        memory_id=memory.id,
        project_id=memory.project_id,
        scope=memory.scope,
        type=memory.type,
        task_id=memory.task_id,
        title=memory.title,
        content=memory.content,
        tags=tuple(memory.tags),
        retrieval_source="semantic",
        fts_rank=-similarity,
        boost_score=0,
        task_id_match=bool(query_task_id) and memory.task_id == query_task_id,
        title_term_hits=(),
        tag_term_hits=(),
        content_term_hits=(),
    )


def _fetch_task_memory_fts_rows(
    *,
    project_id: str,
    safe_fts_query: str,
    max_candidates: int,
) -> list[RawMemoryRow]:
    """Fetch task and eligible project-scope FTS rows in deterministic FTS order."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                m.id,
                m.project_id,
                m.scope,
                m.level,
                m.type,
                m.task_id,
                m.title,
                m.content,
                m.tags,
                bm25(memories_fts) AS fts_rank
            FROM memories AS m
            JOIN memories_fts ON m.rowid = memories_fts.rowid
            WHERE memories_fts MATCH ?
              AND m.project_id = ?
              AND (
                m.scope = 'task'
                OR (
                    m.scope = 'project'
                    AND m.level IN (?, ?)
                    AND m.type IN (?, ?)
                )
              )
            ORDER BY fts_rank ASC, m.id ASC
            LIMIT ?
            """,
            (
                safe_fts_query,
                project_id,
                PROJECT_SCOPE_ELIGIBLE_LEVELS[0],
                PROJECT_SCOPE_ELIGIBLE_LEVELS[1],
                PROJECT_SCOPE_ELIGIBLE_TYPES[0],
                PROJECT_SCOPE_ELIGIBLE_TYPES[1],
                max_candidates,
            ),
        ).fetchall()
    finally:
        conn.close()

    return [
        RawMemoryRow(
            memory_id=row["id"],
            project_id=row["project_id"],
            scope=row["scope"],
            level=row["level"],
            type=row["type"],
            task_id=row["task_id"],
            title=row["title"] or "",
            content=row["content"] or "",
            tags=_split_csv_tags(row["tags"]),
            fts_rank=float(row["fts_rank"]),
        )
        for row in rows
    ]


def retrieve_task_memory_candidates(
    retrieval_query: TaskRetrievalQuery,
    options: TaskMemoryRetrievalOptions | None = None,
) -> TaskMemoryRetrievalResult:
    """Retrieve task memories and scoped project guidance using normalized SQLite FTS."""
    resolved_options = options or TaskMemoryRetrievalOptions()
    project_id = retrieval_query.metadata.project_id
    query_task_id = retrieval_query.metadata.task_id
    safe_fts_query = normalize_fts_query_text(
        retrieval_query.query_text,
        max_terms=resolved_options.max_query_terms,
        max_term_chars=resolved_options.max_term_chars,
    )
    query_terms = _extract_terms_from_safe_query(safe_fts_query)

    if safe_fts_query == EMPTY_FTS_QUERY:
        metadata = TaskMemoryRetrievalMetadata(
            project_id=project_id,
            query_task_id=query_task_id,
            source="fts",
            requested_query_text=retrieval_query.query_text,
            normalized_fts_query=safe_fts_query,
            query_term_count=0,
            query_was_empty=True,
            fallback_used=False,
            fallback_reason=None,
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
        return TaskMemoryRetrievalResult(candidates=(), metadata=metadata)

    try:
        fts_rows = _fetch_task_memory_fts_rows(
            project_id=project_id,
            safe_fts_query=safe_fts_query,
            max_candidates=resolved_options.max_candidates,
        )
    except sqlite3.Error as exc:
        metadata = TaskMemoryRetrievalMetadata(
            project_id=project_id,
            query_task_id=query_task_id,
            source="fts",
            requested_query_text=retrieval_query.query_text,
            normalized_fts_query=safe_fts_query,
            query_term_count=len(query_terms),
            query_was_empty=False,
            fallback_used=True,
            fallback_reason=str(exc),
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
        return TaskMemoryRetrievalResult(candidates=(), metadata=metadata)

    candidates: list[TaskMemoryCandidate] = []
    threshold_filtered_row_count = 0
    threshold_filtered_task_scope_count = 0
    threshold_filtered_project_scope_count = 0
    scanned_task_scope_row_count = sum(1 for row in fts_rows if row.scope == "task")
    scanned_project_scope_row_count = sum(1 for row in fts_rows if row.scope == "project")
    for row in fts_rows:
        title_folded = row.title.casefold()
        content_tokens = _extract_token_set(row.content)
        tag_folded = tuple(tag.casefold() for tag in row.tags)

        title_hits = tuple(term for term in query_terms if term in title_folded)
        tag_hits = tuple(term for term in query_terms if term in tag_folded)
        content_hits = tuple(term for term in query_terms if term in content_tokens)
        has_task_id_match = bool(query_task_id) and row.task_id == query_task_id

        if not _passes_lexical_threshold(
            has_task_id_match=has_task_id_match,
            title_hits=title_hits,
            tag_hits=tag_hits,
            content_hits=content_hits,
            min_content_term_hits_without_title_or_tag=(
                resolved_options.min_content_term_hits_without_title_or_tag
            ),
        ):
            threshold_filtered_row_count += 1
            if row.scope == "task":
                threshold_filtered_task_scope_count += 1
            elif row.scope == "project":
                threshold_filtered_project_scope_count += 1
            continue

        boost_score = (
            (resolved_options.task_id_match_boost if has_task_id_match else 0)
            + (resolved_options.title_term_boost if title_hits else 0)
            + (resolved_options.tag_term_boost if tag_hits else 0)
        )

        candidates.append(
            TaskMemoryCandidate(
                memory_id=row.memory_id,
                project_id=row.project_id,
                scope=row.scope,
                type=row.type,
                task_id=row.task_id,
                title=row.title,
                content=row.content,
                tags=row.tags,
                retrieval_source="fts",
                fts_rank=row.fts_rank,
                boost_score=boost_score,
                task_id_match=has_task_id_match,
                title_term_hits=title_hits,
                tag_term_hits=tag_hits,
                content_term_hits=content_hits,
            )
        )

    ordered_candidates = tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                -candidate.boost_score,
                candidate.fts_rank,
                candidate.memory_id,
            ),
        )
    )

    metadata = TaskMemoryRetrievalMetadata(
        project_id=project_id,
        query_task_id=query_task_id,
        source="fts",
        requested_query_text=retrieval_query.query_text,
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
        threshold_filtered_row_count=threshold_filtered_row_count,
        scanned_task_scope_row_count=scanned_task_scope_row_count,
        scanned_project_scope_row_count=scanned_project_scope_row_count,
        returned_task_scope_candidate_count=sum(
            1 for candidate in ordered_candidates if candidate.scope == "task"
        ),
        returned_project_scope_candidate_count=sum(
            1 for candidate in ordered_candidates if candidate.scope == "project"
        ),
        threshold_filtered_task_scope_count=threshold_filtered_task_scope_count,
        threshold_filtered_project_scope_count=threshold_filtered_project_scope_count,
    )
    return TaskMemoryRetrievalResult(candidates=ordered_candidates, metadata=metadata)


def retrieve_task_memory_semantic_candidates(
    retrieval_query: TaskRetrievalQuery,
    options: TaskMemoryRetrievalOptions | None = None,
    *,
    semantic_storage: SemanticIndexStorage | None = None,
    model_name: str = DEFAULT_SEMANTIC_MODEL_NAME,
) -> TaskMemoryRetrievalResult:
    """Retrieve semantic candidates from local embedding artifacts."""
    resolved_options = options or TaskMemoryRetrievalOptions()
    project_id = retrieval_query.metadata.project_id
    task_id = retrieval_query.metadata.task_id
    query_text = retrieval_query.query_text.strip()
    if not query_text:
        return _empty_semantic_result(
            project_id=project_id,
            task_id=task_id,
            query_text=retrieval_query.query_text,
            max_candidates=resolved_options.max_candidates,
            query_was_empty=True,
            fallback_used=False,
            fallback_reason=None,
        )

    storage = semantic_storage or SemanticIndexStorage(project_id)
    status = storage.get_index_status(
        expected_model_name=model_name,
        expected_model_dim=None,
    )
    if status.status != SemanticIndexStatus.READY:
        return _empty_semantic_result(
            project_id=project_id,
            task_id=task_id,
            query_text=retrieval_query.query_text,
            max_candidates=resolved_options.max_candidates,
            query_was_empty=False,
            fallback_used=True,
            fallback_reason=f"semantic index {status.status.value}: {status.reason}",
        )

    metadata = status.metadata
    if metadata is None:
        return _empty_semantic_result(
            project_id=project_id,
            task_id=task_id,
            query_text=retrieval_query.query_text,
            max_candidates=resolved_options.max_candidates,
            query_was_empty=False,
            fallback_used=True,
            fallback_reason="semantic index ready status missing metadata",
        )

    try:
        np_module, text_embedding_cls = load_semantic_embedding_dependencies()
        raw_matrix: Any = np_module.load(storage.embeddings_path, allow_pickle=False)
        matrix_shape = getattr(raw_matrix, "shape", None)
        if not isinstance(matrix_shape, tuple) or len(matrix_shape) != 2:
            raise ValueError("semantic embeddings matrix must be 2D")
        if matrix_shape[0] != len(metadata.memory_ids):
            raise ValueError("semantic index row count does not match metadata memory_ids")

        embedder = text_embedding_cls(model_name=model_name)
        query_vectors = list(embedder.embed([query_text]))
        if not query_vectors:
            raise ValueError("semantic embedder returned no query vectors")
        query_vector = _to_float_tuple(np_module.asarray(query_vectors[0], dtype=np_module.float32))

        eligible_memories = {
            memory.id: memory
            for memory in _list_project_memories(project_id)
            if _is_semantic_eligible(memory)
        }
        scored_candidates: list[tuple[float, TaskMemoryCandidate]] = []
        for row_index, memory_id in enumerate(metadata.memory_ids):
            memory = eligible_memories.get(memory_id)
            if memory is None:
                continue
            similarity = _cosine_similarity(query_vector, _to_float_tuple(raw_matrix[row_index]))
            scored_candidates.append(
                (
                    similarity,
                    _semantic_candidate_from_memory(
                        memory=memory,
                        similarity=similarity,
                        query_task_id=task_id,
                    ),
                )
            )

        ordered_candidates = tuple(
            candidate
            for _, candidate in sorted(
                scored_candidates,
                key=lambda item: (-item[0], item[1].memory_id),
            )[: resolved_options.max_candidates]
        )
        result_metadata = TaskMemoryRetrievalMetadata(
            project_id=project_id,
            query_task_id=task_id,
            source="semantic",
            requested_query_text=retrieval_query.query_text,
            normalized_fts_query="",
            query_term_count=0,
            query_was_empty=False,
            fallback_used=False,
            fallback_reason=None,
            max_candidates=resolved_options.max_candidates,
            scanned_row_count=matrix_shape[0],
            returned_candidate_count=len(ordered_candidates),
            scanned_task_scope_row_count=sum(
                1 for memory in eligible_memories.values() if memory.scope == "task"
            ),
            scanned_project_scope_row_count=sum(
                1 for memory in eligible_memories.values() if memory.scope == "project"
            ),
            returned_task_scope_candidate_count=sum(
                1 for candidate in ordered_candidates if candidate.scope == "task"
            ),
            returned_project_scope_candidate_count=sum(
                1 for candidate in ordered_candidates if candidate.scope == "project"
            ),
        )
        return TaskMemoryRetrievalResult(candidates=ordered_candidates, metadata=result_metadata)
    except Exception as exc:
        return _empty_semantic_result(
            project_id=project_id,
            task_id=task_id,
            query_text=retrieval_query.query_text,
            max_candidates=resolved_options.max_candidates,
            query_was_empty=False,
            fallback_used=True,
            fallback_reason=f"semantic retrieval failed: {exc}",
        )
