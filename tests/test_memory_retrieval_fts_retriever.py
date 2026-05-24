"""Tests for task-scope FTS retrieval candidates."""

import sqlite3

from engram.memory_retrieval.fts_retriever import retrieve_task_memory_candidates
from engram.memory_retrieval.query_builder import (
    RetrievalQueryMetadata,
    TaskRetrievalQuery,
    build_task_retrieval_query,
)
from engram.models.memory import Memory
from engram.models.project import Project
from engram.models.task import Task


def _build_test_query(*, project_id: str, task_id: str, query_text: str) -> TaskRetrievalQuery:
    metadata = RetrievalQueryMetadata(
        task_id=task_id,
        project_id=project_id,
        phase_id=None,
        phase_title=None,
        included_fields=("task.title",),
        omitted_fields=(),
        truncated_fields=(),
        max_query_chars=1200,
        field_char_limit=220,
        uncapped_query_char_count=len(query_text),
        query_char_count=len(query_text),
        query_was_capped=False,
    )
    return TaskRetrievalQuery(
        query_text=query_text,
        fragments=(f"task.title: {query_text}",),
        metadata=metadata,
    )


def test_retriever_returns_task_scope_matches_and_excludes_other_scope_and_projects(
    project,
) -> None:
    task = Task.create(project_id=project.id, title="Implement retrieval helper")
    same_project_title = Memory.create(
        project_id=project.id,
        type="lesson",
        title="FTS helper title match",
        content="Notes on retrieval behavior.",
        scope="task",
        task_id=task.id,
        tags=["retrieval"],
    )
    same_project_content = Memory.create(
        project_id=project.id,
        type="snippet",
        title="SQLite BM25 note",
        content="Retriever should find this by helper content match.",
        scope="task",
        task_id=None,
        tags=["sqlite"],
    )
    same_project_tag = Memory.create(
        project_id=project.id,
        type="lesson",
        title="Tag-targeted memory",
        content="Unrelated body text.",
        scope="task",
        task_id=None,
        tags=["helper"],
    )

    Memory.create(
        project_id=project.id,
        type="constraint",
        title="Project guardrail with helper keyword",
        content="Must not appear in task-memory retrieval candidates.",
        scope="project",
        level="L1",
    )

    other_project = Project.create(
        "other-project",
        "Other project",
        summary="Secondary fixture project",
        repo_paths=["/tmp/other"],
    )
    Memory.create(
        project_id=other_project.id,
        type="lesson",
        title="Other project helper memory",
        content="Should be filtered by project id.",
        scope="task",
        tags=["helper"],
    )

    retrieval_query = _build_test_query(
        project_id=project.id,
        task_id=task.id,
        query_text="helper retrieval sqlite",
    )

    result = retrieve_task_memory_candidates(retrieval_query)
    returned_ids = [candidate.memory_id for candidate in result.candidates]

    assert same_project_title.id in returned_ids
    assert same_project_content.id in returned_ids
    assert same_project_tag.id in returned_ids
    assert all(candidate.scope == "task" for candidate in result.candidates)
    assert all(candidate.project_id == project.id for candidate in result.candidates)


def test_retriever_applies_task_id_boost_deterministically(project) -> None:
    task = Task.create(project_id=project.id, title="Rank with task id boost")
    boosted_memory = Memory.create(
        project_id=project.id,
        type="lesson",
        title="Boosted memory",
        content="helper helper helper",
        scope="task",
        task_id=task.id,
    )
    non_boosted_memory = Memory.create(
        project_id=project.id,
        type="lesson",
        title="Non boosted memory",
        content="helper helper helper",
        scope="task",
        task_id=None,
    )
    retrieval_query = _build_test_query(
        project_id=project.id,
        task_id=task.id,
        query_text="helper",
    )

    first = retrieve_task_memory_candidates(retrieval_query)
    second = retrieve_task_memory_candidates(retrieval_query)

    assert first == second
    assert [candidate.memory_id for candidate in first.candidates[:2]] == [
        boosted_memory.id,
        non_boosted_memory.id,
    ]
    assert first.candidates[0].task_id_match is True
    assert first.candidates[0].boost_score > first.candidates[1].boost_score


def test_retriever_handles_empty_or_malformed_queries_without_crashing(project) -> None:
    task = Task.create(project_id=project.id, title="Empty query behavior")
    Memory.create(
        project_id=project.id,
        type="lesson",
        title="Memory that should not be returned",
        content="No query terms should return no candidates.",
        scope="task",
        task_id=task.id,
    )
    retrieval_query = _build_test_query(
        project_id=project.id,
        task_id=task.id,
        query_text="   ::: ||| --- (( ))   ",
    )

    result = retrieve_task_memory_candidates(retrieval_query)

    assert result.candidates == ()
    assert result.metadata.query_was_empty is True
    assert result.metadata.fallback_used is False
    assert result.metadata.fallback_reason is None
    assert result.metadata.scanned_row_count == 0
    assert result.metadata.returned_candidate_count == 0


def test_retriever_falls_back_when_fts_query_execution_fails(project, monkeypatch) -> None:
    task = Task.create(project_id=project.id, title="Malformed FTS fallback")
    retrieval_query = _build_test_query(
        project_id=project.id,
        task_id=task.id,
        query_text="helper",
    )

    def _raise_fts_error(*, project_id: str, safe_fts_query: str, max_candidates: int):
        raise sqlite3.OperationalError("malformed MATCH expression")

    monkeypatch.setattr(
        "engram.memory_retrieval.fts_retriever._fetch_task_scope_fts_rows",
        _raise_fts_error,
    )

    result = retrieve_task_memory_candidates(retrieval_query)

    assert result.candidates == ()
    assert result.metadata.query_was_empty is False
    assert result.metadata.fallback_used is True
    assert result.metadata.fallback_reason == "malformed MATCH expression"
    assert result.metadata.scanned_row_count == 0
    assert result.metadata.returned_candidate_count == 0


def test_retriever_falls_back_when_fts_table_is_unavailable(project) -> None:
    task = Task.create(project_id=project.id, title="Missing FTS table fallback")
    Memory.create(
        project_id=project.id,
        type="lesson",
        title="Task memory",
        content="Retriever should degrade gracefully.",
        scope="task",
        task_id=task.id,
    )

    from engram.db import get_db_connection

    conn = get_db_connection()
    conn.execute("DROP TABLE memories_fts")
    conn.commit()
    conn.close()

    retrieval_query = _build_test_query(
        project_id=project.id,
        task_id=task.id,
        query_text="retriever",
    )
    result = retrieve_task_memory_candidates(retrieval_query)

    assert result.candidates == ()
    assert result.metadata.query_was_empty is False
    assert result.metadata.fallback_used is True
    assert result.metadata.fallback_reason is not None
    assert "no such table" in result.metadata.fallback_reason
    assert result.metadata.scanned_row_count == 0
    assert result.metadata.returned_candidate_count == 0


def test_phase9_scope_gap_misses_project_scope_docs_guidance(project) -> None:
    """Phase 9 regression: docs guidance in project scope is missed for user-manual tasks."""
    task = Task.create(
        project_id=project.id,
        title="Create User Manual",
        description="Prepare public release documentation and command help output.",
        acceptance="Manual includes command output examples and release checks.",
    )
    docs_guidance = Memory.create(
        project_id=project.id,
        type="lesson",
        title="Public docs must match CLI help",
        content="Before release, verify README and USER_MANUAL align with --help output.",
        scope="project",
        level="L1",
    )
    retrieval_internal = Memory.create(
        project_id=project.id,
        type="lesson",
        title="Task retrieval debug output notes",
        content="Debug retrieval query output for startup tests.",
        scope="task",
        task_id=None,
        tags=["retrieval", "debug"],
    )

    retrieval_query = build_task_retrieval_query(task)
    result = retrieve_task_memory_candidates(retrieval_query)
    returned_ids = [candidate.memory_id for candidate in result.candidates]

    assert docs_guidance.id not in returned_ids
    assert retrieval_internal.id in returned_ids
    assert all(candidate.scope == "task" for candidate in result.candidates)


def test_phase9_generic_terms_can_pull_irrelevant_retrieval_internals(project) -> None:
    """Phase 9 regression: generic terms can pull retrieval internals into release tasks."""
    task = Task.create(
        project_id=project.id,
        title="Prepare repository for public release",
        description="Prepare docs and final output checks for release readiness.",
    )
    retrieval_internal = Memory.create(
        project_id=project.id,
        type="lesson",
        title="Task output retrieval diagnostics",
        content="Task query output and retrieval debugging for startup internals.",
        scope="task",
        task_id=None,
    )
    retrieval_query = build_task_retrieval_query(task)

    result = retrieve_task_memory_candidates(retrieval_query)

    assert [candidate.memory_id for candidate in result.candidates] == [retrieval_internal.id]
    assert result.candidates[0].task_id_match is False
    assert "task" in result.candidates[0].title_term_hits
