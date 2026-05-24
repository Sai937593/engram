"""Tests for FTS-safe retrieval query normalization."""

from engram.memory_retrieval.fts_query import EMPTY_FTS_QUERY, normalize_fts_query_text
from engram.memory_retrieval.query_builder import build_task_retrieval_query
from engram.models.memory import Memory
from engram.models.task import Task


def test_normalize_fts_query_text_returns_empty_phrase_for_blank_or_punctuation() -> None:
    assert normalize_fts_query_text(None) == EMPTY_FTS_QUERY
    assert normalize_fts_query_text("") == EMPTY_FTS_QUERY
    assert normalize_fts_query_text("   ::: ||| --- (( ))   ") == EMPTY_FTS_QUERY


def test_normalize_fts_query_text_quotes_and_deduplicates_terms() -> None:
    raw_query = "task.title: WAL-phase | task.tags: sqlite, FTS5, sqlite -- NOT"

    normalized = normalize_fts_query_text(raw_query)

    assert (
        normalized
        == '"task" OR "title" OR "WAL" OR "phase" OR "tags" OR "sqlite" OR "FTS5" OR "NOT"'
    )


def test_memory_search_handles_malformed_fts_input_without_raising(project) -> None:
    Memory.create(
        project_id=project.id,
        type="lesson",
        title="WAL concurrency",
        content="WAL concurrent phase 5 startup handling.",
        scope="project",
        level="L3",
    )

    malformed_query = 'task.title: WAL concurrent | phase-5 AND OR NOT "broken'
    results = Memory.search(malformed_query)

    assert [memory.title for memory in results] == ["WAL concurrency"]


def test_query_builder_text_normalizes_to_searchable_fts_query(project) -> None:
    task = Task(
        id="task-fts-001",
        project_id=project.id,
        title="Implement WAL retrieval safety",
        description="Handle punctuation-heavy FTS parser edge cases.",
        acceptance="Query text should be normalized for safe SQLite MATCH usage.",
        tags=["retrieval", "phase-5", "sqlite"],
    )
    Memory.create(
        project_id=project.id,
        type="snippet",
        title="FTS normalization note",
        content="WAL retrieval safety for SQLite phase 5 startup queries.",
        scope="task",
        task_id=task.id,
        level=None,
    )

    retrieval_query = build_task_retrieval_query(task)
    safe_fts_query = normalize_fts_query_text(retrieval_query.query_text)
    results = Memory.search(safe_fts_query)

    assert ":" in retrieval_query.query_text
    assert "|" in retrieval_query.query_text
    assert ":" not in safe_fts_query
    assert "|" not in safe_fts_query
    assert [memory.title for memory in results] == ["FTS normalization note"]
