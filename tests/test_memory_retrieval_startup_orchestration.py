"""Tests for startup task-memory retrieval orchestration."""

from engram.memory_retrieval import orchestrate_startup_task_memory_retrieval
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
