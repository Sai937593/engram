"""Database and coordinate logic for task memory FTS retrieval."""

from __future__ import annotations

import sqlite3

from engram.db import get_db_connection
from engram.memory_retrieval.fts_query import (
    EMPTY_FTS_QUERY,
    normalize_fts_query_text,
)
from engram.memory_retrieval.fts_retriever.scoring import (
    _extract_token_set,
    _passes_lexical_threshold,
    build_empty_fts_meta,
    build_fts_meta,
    compute_boost_score,
)
from engram.memory_retrieval.fts_retriever.utils import (
    _extract_terms_from_safe_query,
    _split_csv_tags,
)
from engram.memory_retrieval.query_builder import TaskRetrievalQuery
from engram.memory_retrieval.retrieval_contract import (
    RawMemoryRow,
    TaskMemoryCandidate,
    TaskMemoryRetrievalOptions,
    TaskMemoryRetrievalResult,
)

PROJECT_SCOPE_ELIGIBLE_LEVELS = ("L2", "L3")
PROJECT_SCOPE_ELIGIBLE_TYPES = ("lesson", "decision")


def _fetch_task_memory_fts_rows(
    *,
    project_id: str,
    safe_fts_query: str,
    max_candidates: int,
) -> list[RawMemoryRow]:
    """Fetch task and eligible project-scope FTS rows in DB."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT m.id, m.project_id, m.scope, m.level, m.type, m.task_id, m.title, m.content, m.tags,
                   bm25(memories_fts) AS fts_rank
            FROM memories AS m
            JOIN memories_fts ON m.rowid = memories_fts.rowid
            WHERE memories_fts MATCH ? AND m.project_id = ?
              AND m.superseded_by IS NULL
              AND (m.scope = 'task' OR (m.scope = 'project' AND m.level IN (?, ?) AND m.type IN (?, ?)))
            ORDER BY fts_rank ASC, m.id ASC LIMIT ?
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
    """Retrieve task memories and scoped project guidance using SQLite FTS."""
    resolved = options or TaskMemoryRetrievalOptions()
    project_id = retrieval_query.metadata.project_id
    query_task_id = retrieval_query.metadata.task_id
    safe_query = normalize_fts_query_text(
        retrieval_query.query_text,
        max_terms=resolved.max_query_terms,
        max_term_chars=resolved.max_term_chars,
    )
    terms = _extract_terms_from_safe_query(safe_query)

    if safe_query == EMPTY_FTS_QUERY:
        meta = build_empty_fts_meta(
            project_id,
            query_task_id,
            retrieval_query.query_text,
            safe_query,
            terms,
            resolved,
            query_was_empty=True,
        )
        return TaskMemoryRetrievalResult(candidates=(), metadata=meta)

    try:
        fts_rows = _fetch_task_memory_fts_rows(
            project_id=project_id, safe_fts_query=safe_query, max_candidates=resolved.max_candidates
        )
    except sqlite3.Error as exc:
        meta = build_empty_fts_meta(
            project_id,
            query_task_id,
            retrieval_query.query_text,
            safe_query,
            terms,
            resolved,
            fallback_used=True,
            fallback_reason=str(exc),
        )
        return TaskMemoryRetrievalResult(candidates=(), metadata=meta)

    candidates: list[TaskMemoryCandidate] = []
    filtered = 0
    filtered_task = 0
    filtered_project = 0
    scanned_task = sum(1 for row in fts_rows if row.scope == "task")
    scanned_project = sum(1 for row in fts_rows if row.scope == "project")

    for row in fts_rows:
        title_folded = row.title.casefold()
        content_tokens = _extract_token_set(row.content)
        tag_folded = tuple(tag.casefold() for tag in row.tags)

        title_hits = tuple(term for term in terms if term in title_folded)
        tag_hits = tuple(term for term in terms if term in tag_folded)
        content_hits = tuple(term for term in terms if term in content_tokens)
        has_match = bool(query_task_id) and row.task_id == query_task_id

        if not _passes_lexical_threshold(
            has_task_id_match=has_match,
            title_hits=title_hits,
            tag_hits=tag_hits,
            content_hits=content_hits,
            min_content_term_hits_without_title_or_tag=resolved.min_content_term_hits_without_title_or_tag,
        ):
            filtered += 1
            if row.scope == "task":
                filtered_task += 1
            elif row.scope == "project":
                filtered_project += 1
            continue

        boost = compute_boost_score(has_match, title_hits, tag_hits, resolved)
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
                boost_score=boost,
                task_id_match=has_match,
                title_term_hits=title_hits,
                tag_term_hits=tag_hits,
                content_term_hits=content_hits,
            )
        )

    ordered = tuple(sorted(candidates, key=lambda c: (-c.boost_score, c.fts_rank, c.memory_id)))
    meta = build_fts_meta(
        project_id,
        query_task_id,
        retrieval_query.query_text,
        safe_query,
        terms,
        resolved,
        fts_rows,
        ordered,
        filtered,
        scanned_task,
        scanned_project,
        filtered_task,
        filtered_project,
    )
    return TaskMemoryRetrievalResult(candidates=ordered, metadata=meta)
