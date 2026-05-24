"""FTS retrieval over task memories and eligible project guidance candidates."""

from __future__ import annotations

import sqlite3

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

PROJECT_SCOPE_ELIGIBLE_LEVELS = ("L2", "L3")
PROJECT_SCOPE_ELIGIBLE_TYPES = ("lesson", "decision")


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
        )
        return TaskMemoryRetrievalResult(candidates=(), metadata=metadata)

    candidates: list[TaskMemoryCandidate] = []
    for row in fts_rows:
        title_folded = row.title.casefold()
        tag_folded = tuple(tag.casefold() for tag in row.tags)

        title_hits = tuple(term for term in query_terms if term in title_folded)
        tag_hits = tuple(term for term in query_terms if term in tag_folded)
        has_task_id_match = bool(query_task_id) and row.task_id == query_task_id

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
    )
    return TaskMemoryRetrievalResult(candidates=ordered_candidates, metadata=metadata)
