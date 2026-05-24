"""Tests for task retrieval query builder."""

from engram.memory_retrieval.query_builder import (
    RetrievalQueryBuilderOptions,
    build_task_retrieval_query,
)
from engram.models.phase import Phase
from engram.models.task import Task


def test_query_builder_handles_minimal_task():
    task = Task(
        id="task001",
        project_id="proj001",
        title="Ship retrieval API",
    )

    query = build_task_retrieval_query(task)

    assert query.query_text == "task.title: Ship retrieval API"
    assert query.fragments == ("task.title: Ship retrieval API",)
    assert query.metadata.task_id == "task001"
    assert query.metadata.project_id == "proj001"
    assert query.metadata.included_fields == ("task.title",)
    assert "task.description" in query.metadata.omitted_fields
    assert "task.acceptance" in query.metadata.omitted_fields
    assert "task.tags" in query.metadata.omitted_fields
    assert "task.evidence" in query.metadata.omitted_fields


def test_query_builder_is_deterministic_with_phase_and_context():
    task = Task(
        id="task002",
        project_id="proj001",
        title="Implement retrieval query builder",
        description="Build deterministic query text.",
        acceptance="Includes task and phase context for retrieval.",
        tags=["memory", "retrieval", "memory"],
    )
    phase = Phase(
        id="phase002",
        project_id="proj001",
        title="Memory Retrieval Phase 4",
        description="Create a backend-agnostic query builder.",
        acceptance="Startup and related-to-task share the same builder.",
    )
    context = {
        "repo": "engram",
        "area": "startup retrieval",
    }
    options = RetrievalQueryBuilderOptions(field_char_limit=120)

    first = build_task_retrieval_query(task, active_phase=phase, context=context, options=options)
    second = build_task_retrieval_query(task, active_phase=phase, context=context, options=options)

    assert first == second
    assert first.metadata.phase_id == "phase002"
    assert "task.tags: memory, retrieval" in first.query_text
    assert "phase.title: Memory Retrieval Phase 4" in first.query_text
    assert "context.area: startup retrieval" in first.query_text
    assert "context.repo: engram" in first.query_text
    assert "phase.evidence" in first.metadata.omitted_fields


def test_query_builder_does_not_perform_database_search(monkeypatch):
    task = Task(
        id="task003",
        project_id="proj001",
        title="No DB query required",
        description="Only build retrieval text.",
    )
    search_call_count = {"count": 0}

    def _forbidden_memory_search(*args, **kwargs):
        search_call_count["count"] += 1
        raise AssertionError("Memory.search should not be used by query builder.")

    monkeypatch.setattr("engram.models.memory.Memory.search", _forbidden_memory_search)

    query = build_task_retrieval_query(task)

    assert query.query_text.startswith("task.title: No DB query required")
    assert search_call_count["count"] == 0
