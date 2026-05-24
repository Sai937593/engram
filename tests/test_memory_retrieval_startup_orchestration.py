"""Tests for startup task-memory retrieval orchestration."""

from engram.memory_retrieval import (
    TaskMemoryRetrievalMetadata,
    TaskMemoryRetrievalOptions,
    TaskMemoryRetrievalResult,
    orchestrate_startup_task_memory_retrieval,
)
from engram.models.memory import Memory
from engram.models.phase import Phase
from engram.models.task import Task


def test_startup_orchestration_returns_empty_pack_when_no_task_selected(project) -> None:
    phase = Phase.create(project_id=project.id, title="Phase 7", status="active")

    result = orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=phase,
        selected_task=None,
    )

    assert result.query is None
    assert result.retrieval_metadata.project_id == project.id
    assert result.retrieval_metadata.query_task_id == ""
    assert result.retrieval_metadata.source == "none"
    assert result.retrieval_metadata.fallback_used is False
    assert result.pack_result.items == ()
    assert result.pack_result.metadata.selected_item_count == 0


def test_startup_orchestration_selects_relevant_task_memories(project) -> None:
    phase = Phase.create(
        project_id=project.id,
        title="Memory Retrieval",
        status="active",
        description="Integrate startup retrieval.",
    )
    task = Task.create(
        project_id=project.id,
        title="Integrate FTS retrieval into startup",
        description="Retrieve and pack task memories.",
        phase_id=phase.id,
        status="in-progress",
        tags=["retrieval", "startup"],
    )
    relevant = Memory.create(
        project_id=project.id,
        type="lesson",
        title="Startup retrieval fallback",
        content="Use fallback metadata when retrieval fails.",
        scope="task",
        task_id=task.id,
        tags=["retrieval"],
    )
    Memory.create(
        project_id=project.id,
        type="constraint",
        title="Project guardrail",
        content="Should not be in task-scope retrieval candidates.",
        scope="project",
        level="L1",
    )

    result = orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=phase,
        selected_task=task,
    )

    assert result.query is not None
    assert result.query.metadata.task_id == task.id
    assert result.retrieval_metadata.fallback_used is False
    assert result.retrieval_metadata.returned_candidate_count >= 1
    assert any(item.memory_id == relevant.id for item in result.pack_result.items)
    assert result.pack_result.metadata.query_task_id == task.id
    assert result.pack_result.metadata.selected_item_count >= 1


def test_startup_orchestration_returns_empty_pack_for_no_match(project) -> None:
    phase = Phase.create(project_id=project.id, title="Phase Empty Match", status="active")
    task = Task.create(
        project_id=project.id,
        title="No match task",
        description="Unique terms that have no stored memory rows.",
        phase_id=phase.id,
        status="in-progress",
    )

    result = orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=phase,
        selected_task=task,
    )

    assert result.query is not None
    assert result.retrieval_metadata.fallback_used is False
    assert result.retrieval_metadata.returned_candidate_count == 0
    assert result.pack_result.items == ()
    assert result.pack_result.metadata.selected_item_count == 0


def test_startup_orchestration_converts_retriever_exceptions_to_fallback_metadata(
    project,
    monkeypatch,
) -> None:
    phase = Phase.create(project_id=project.id, title="Phase Retrieval Error", status="active")
    task = Task.create(
        project_id=project.id,
        title="Handle retrieval exception",
        phase_id=phase.id,
        status="in-progress",
    )

    def _raise_unexpected_error(*args, **kwargs):
        raise RuntimeError("unexpected retrieval failure")

    monkeypatch.setattr(
        "engram.memory_retrieval.startup_orchestration.retrieve_task_memory_candidates",
        _raise_unexpected_error,
    )

    result = orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=phase,
        selected_task=task,
    )

    assert result.query is not None
    assert result.retrieval_metadata.fallback_used is True
    assert result.retrieval_metadata.fallback_reason == "unexpected retrieval failure"
    assert result.retrieval_metadata.returned_candidate_count == 0
    assert result.pack_result.items == ()
    assert result.pack_result.metadata.selected_item_count == 0


def test_startup_orchestration_converts_query_builder_exceptions_to_fallback_metadata(
    project,
    monkeypatch,
) -> None:
    phase = Phase.create(project_id=project.id, title="Phase Query Error", status="active")
    task = Task.create(
        project_id=project.id,
        title="Handle query exception",
        phase_id=phase.id,
        status="in-progress",
    )

    def _raise_query_error(*args, **kwargs):
        raise RuntimeError("query builder failure")

    monkeypatch.setattr(
        "engram.memory_retrieval.startup_orchestration.build_task_retrieval_query",
        _raise_query_error,
    )

    result = orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=phase,
        selected_task=task,
    )

    assert result.query is None
    assert result.retrieval_metadata.fallback_used is True
    assert result.retrieval_metadata.fallback_reason == "query builder failure"
    assert result.retrieval_metadata.returned_candidate_count == 0
    assert result.pack_result.items == ()
    assert result.pack_result.metadata.selected_item_count == 0


def test_startup_orchestration_converts_pack_exceptions_to_fallback_metadata(
    project,
    monkeypatch,
) -> None:
    phase = Phase.create(project_id=project.id, title="Phase Pack Error", status="active")
    task = Task.create(
        project_id=project.id,
        title="Handle pack exception",
        phase_id=phase.id,
        status="in-progress",
    )

    def _raise_pack_error(*args, **kwargs):
        raise RuntimeError("pack failure")

    monkeypatch.setattr(
        "engram.memory_retrieval.startup_orchestration.pack_task_memories",
        _raise_pack_error,
    )

    result = orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=phase,
        selected_task=task,
    )

    assert result.query is not None
    assert result.retrieval_metadata.fallback_used is True
    assert result.retrieval_metadata.fallback_reason == "pack failure"
    assert result.retrieval_metadata.returned_candidate_count == 0
    assert result.pack_result.items == ()
    assert result.pack_result.metadata.selected_item_count == 0


def test_startup_orchestration_timeout_after_retrieval_returns_fallback_metadata(
    project,
    monkeypatch,
) -> None:
    phase = Phase.create(project_id=project.id, title="Phase Timeout", status="active")
    task = Task.create(
        project_id=project.id,
        title="Handle retrieval timeout",
        phase_id=phase.id,
        status="in-progress",
    )
    retrieval_options = TaskMemoryRetrievalOptions(
        max_candidates=20,
        orchestration_timeout_seconds=1.0,
    )

    def _mock_monotonic():
        values = iter((0.0, 0.0, 1.2))
        return lambda: next(values)

    def _mock_retriever(*args, **kwargs):
        return TaskMemoryRetrievalResult(
            candidates=(),
            metadata=TaskMemoryRetrievalMetadata(
                project_id=project.id,
                query_task_id=task.id,
                source="fts",
                requested_query_text="timeout query",
                normalized_fts_query='"timeout"',
                query_term_count=1,
                query_was_empty=False,
                fallback_used=False,
                fallback_reason=None,
                max_candidates=20,
                scanned_row_count=0,
                returned_candidate_count=0,
            ),
        )

    monkeypatch.setattr(
        "engram.memory_retrieval.startup_orchestration.monotonic",
        _mock_monotonic(),
    )
    monkeypatch.setattr(
        "engram.memory_retrieval.startup_orchestration.retrieve_task_memory_candidates",
        _mock_retriever,
    )

    result = orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=phase,
        selected_task=task,
        retrieval_options=retrieval_options,
    )

    assert result.query is not None
    assert result.retrieval_metadata.fallback_used is True
    assert result.retrieval_metadata.fallback_reason is not None
    assert "timed out" in result.retrieval_metadata.fallback_reason
    assert "during retrieval" in result.retrieval_metadata.fallback_reason
    assert result.retrieval_metadata.returned_candidate_count == 0
    assert result.pack_result.items == ()
