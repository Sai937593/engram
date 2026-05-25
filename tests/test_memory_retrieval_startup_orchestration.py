"""Tests for startup task-memory retrieval orchestration."""

from engram.memory_retrieval import (
    TaskMemoryCandidate,
    TaskMemoryRetrievalMetadata,
    TaskMemoryRetrievalOptions,
    TaskMemoryRetrievalResult,
    orchestrate_startup_task_memory_retrieval,
)
from engram.models.memory import Memory
from engram.models.phase import Phase
from engram.models.task import Task


def _candidate(
    *,
    memory_id: str,
    project_id: str,
    task_id: str | None,
    title: str,
    content: str,
    retrieval_source: str,
    fts_rank: float,
    boost_score: int,
    task_id_match: bool,
    title_term_hits: tuple[str, ...] | None = None,
) -> TaskMemoryCandidate:
    return TaskMemoryCandidate(
        memory_id=memory_id,
        project_id=project_id,
        scope="task",
        type="lesson",
        task_id=task_id,
        title=title,
        content=content,
        tags=("retrieval",),
        retrieval_source=retrieval_source,
        fts_rank=fts_rank,
        boost_score=boost_score,
        task_id_match=task_id_match,
        title_term_hits=(
            title_term_hits
            if title_term_hits is not None
            else (("retrieval",) if retrieval_source == "fts" else ())
        ),
        tag_term_hits=(),
        content_term_hits=(),
    )


def _metadata(
    *,
    project_id: str,
    task_id: str,
    source: str,
    fallback_used: bool = False,
    fallback_reason: str | None = None,
    returned_candidate_count: int = 0,
    max_candidates: int = 20,
) -> TaskMemoryRetrievalMetadata:
    return TaskMemoryRetrievalMetadata(
        project_id=project_id,
        query_task_id=task_id,
        source=source,
        requested_query_text="task.title: retrieval",
        normalized_fts_query='"retrieval"',
        query_term_count=1,
        query_was_empty=False,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        max_candidates=max_candidates,
        scanned_row_count=2,
        returned_candidate_count=returned_candidate_count,
    )


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


def test_startup_orchestration_prefers_empty_pack_over_weak_fill(project) -> None:
    phase = Phase.create(project_id=project.id, title="Phase Weak Fill", status="active")
    task = Task.create(
        project_id=project.id,
        title="Prepare release manual",
        description="Write public docs checklist.",
        phase_id=phase.id,
        status="in-progress",
    )
    Memory.create(
        project_id=project.id,
        type="lesson",
        title="Internal retrieval note",
        content="release manual internals for unrelated debug checks",
        scope="task",
        task_id=None,
    )

    result = orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=phase,
        selected_task=task,
    )

    assert result.retrieval_metadata.returned_candidate_count == 1
    assert result.pack_result.items == ()
    assert result.pack_result.metadata.selected_item_count == 0
    assert result.pack_result.metadata.relevance_filtered_count == 1


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


def test_startup_orchestration_fts_only_path_surfaces_semantic_missing_status(project) -> None:
    phase = Phase.create(project_id=project.id, title="Phase FTS Only", status="active")
    task = Task.create(
        project_id=project.id,
        title="FTS-only retrieval",
        phase_id=phase.id,
        status="in-progress",
    )
    fts_memory = Memory.create(
        project_id=project.id,
        type="lesson",
        title="FTS fallback memory",
        content="Keep FTS retrieval available when semantic index is missing.",
        scope="task",
        task_id=task.id,
        tags=["retrieval"],
    )

    result = orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=phase,
        selected_task=task,
    )

    selected_ids = [item.memory_id for item in result.pack_result.items]
    assert fts_memory.id in selected_ids
    assert result.retrieval_metadata.semantic_status == "missing"
    assert result.retrieval_metadata.semantic_fallback_used is True
    assert result.retrieval_metadata.fts_returned_candidate_count >= 1
    assert result.retrieval_metadata.semantic_returned_candidate_count == 0


def test_startup_orchestration_semantic_only_candidates_are_packable(
    project,
    monkeypatch,
) -> None:
    phase = Phase.create(project_id=project.id, title="Phase Semantic Only", status="active")
    task = Task.create(
        project_id=project.id,
        title="Semantic-only retrieval",
        phase_id=phase.id,
        status="in-progress",
    )
    semantic_candidate = _candidate(
        memory_id="sem-1",
        project_id=project.id,
        task_id=task.id,
        title="Semantic candidate",
        content="Semantic-only candidate still packs.",
        retrieval_source="semantic",
        fts_rank=-0.95,
        boost_score=0,
        task_id_match=True,
    )
    monkeypatch.setattr(
        "engram.memory_retrieval.startup_orchestration.retrieve_task_memory_candidates",
        lambda *args, **kwargs: TaskMemoryRetrievalResult(
            candidates=(),
            metadata=_metadata(
                project_id=project.id,
                task_id=task.id,
                source="fts",
                returned_candidate_count=0,
            ),
        ),
    )
    monkeypatch.setattr(
        "engram.memory_retrieval.startup_orchestration.retrieve_task_memory_semantic_candidates",
        lambda *args, **kwargs: TaskMemoryRetrievalResult(
            candidates=(semantic_candidate,),
            metadata=_metadata(
                project_id=project.id,
                task_id=task.id,
                source="semantic",
                returned_candidate_count=1,
            ),
        ),
    )

    result = orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=phase,
        selected_task=task,
    )

    assert [item.memory_id for item in result.pack_result.items] == ["sem-1"]
    assert result.retrieval_metadata.semantic_status == "ready"
    assert result.retrieval_metadata.semantic_returned_candidate_count == 1
    assert result.retrieval_metadata.returned_candidate_count == 1


def test_startup_orchestration_mixed_fusion_merges_duplicates_and_preserves_fts_order(
    project,
    monkeypatch,
) -> None:
    phase = Phase.create(project_id=project.id, title="Phase Mixed Fusion", status="active")
    task = Task.create(
        project_id=project.id,
        title="Mixed retrieval fusion",
        phase_id=phase.id,
        status="in-progress",
    )
    fts_exact = _candidate(
        memory_id="mem-fts-exact",
        project_id=project.id,
        task_id=task.id,
        title="Exact FTS hit",
        content="Direct lexical hit.",
        retrieval_source="fts",
        fts_rank=-0.2,
        boost_score=1,
        task_id_match=True,
    )
    fts_duplicate = _candidate(
        memory_id="mem-shared",
        project_id=project.id,
        task_id=task.id,
        title="Shared hit",
        content="Appears in both channels.",
        retrieval_source="fts",
        fts_rank=-0.1,
        boost_score=0,
        task_id_match=False,
        title_term_hits=(),
    )
    semantic_duplicate = _candidate(
        memory_id="mem-shared",
        project_id=project.id,
        task_id=task.id,
        title="Shared hit semantic",
        content="Semantic duplicate of shared id.",
        retrieval_source="semantic",
        fts_rank=-0.99,
        boost_score=0,
        task_id_match=False,
    )
    semantic_only = _candidate(
        memory_id="mem-sem-only",
        project_id=project.id,
        task_id=task.id,
        title="Semantic only",
        content="Only semantic channel has this item.",
        retrieval_source="semantic",
        fts_rank=-0.8,
        boost_score=0,
        task_id_match=False,
    )
    monkeypatch.setattr(
        "engram.memory_retrieval.startup_orchestration.retrieve_task_memory_candidates",
        lambda *args, **kwargs: TaskMemoryRetrievalResult(
            candidates=(fts_exact, fts_duplicate),
            metadata=_metadata(
                project_id=project.id,
                task_id=task.id,
                source="fts",
                returned_candidate_count=2,
            ),
        ),
    )
    monkeypatch.setattr(
        "engram.memory_retrieval.startup_orchestration.retrieve_task_memory_semantic_candidates",
        lambda *args, **kwargs: TaskMemoryRetrievalResult(
            candidates=(semantic_duplicate, semantic_only),
            metadata=_metadata(
                project_id=project.id,
                task_id=task.id,
                source="semantic",
                returned_candidate_count=2,
            ),
        ),
    )

    result = orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=phase,
        selected_task=task,
    )

    fused = result.retrieval_candidates
    assert [candidate.memory_id for candidate in fused] == [
        "mem-fts-exact",
        "mem-sem-only",
        "mem-shared",
    ]
    assert fused[0].retrieval_source == "fts"
    assert fused[2].retrieval_source == "fts+semantic"
    assert result.retrieval_metadata.fused_duplicate_count == 1
    assert result.retrieval_metadata.exact_fts_preserved_count >= 1


def test_startup_orchestration_uses_semantic_when_fts_channel_falls_back(
    project,
    monkeypatch,
) -> None:
    phase = Phase.create(project_id=project.id, title="Phase FTS Fallback", status="active")
    task = Task.create(
        project_id=project.id,
        title="FTS fallback with semantic",
        phase_id=phase.id,
        status="in-progress",
    )
    semantic_candidate = _candidate(
        memory_id="sem-fallback",
        project_id=project.id,
        task_id=task.id,
        title="Semantic fallback candidate",
        content="Semantic candidate is available during FTS fallback.",
        retrieval_source="semantic",
        fts_rank=-0.6,
        boost_score=0,
        task_id_match=False,
    )
    monkeypatch.setattr(
        "engram.memory_retrieval.startup_orchestration.retrieve_task_memory_candidates",
        lambda *args, **kwargs: TaskMemoryRetrievalResult(
            candidates=(),
            metadata=_metadata(
                project_id=project.id,
                task_id=task.id,
                source="fts",
                fallback_used=True,
                fallback_reason="fts table unavailable",
                returned_candidate_count=0,
            ),
        ),
    )
    monkeypatch.setattr(
        "engram.memory_retrieval.startup_orchestration.retrieve_task_memory_semantic_candidates",
        lambda *args, **kwargs: TaskMemoryRetrievalResult(
            candidates=(semantic_candidate,),
            metadata=_metadata(
                project_id=project.id,
                task_id=task.id,
                source="semantic",
                returned_candidate_count=1,
            ),
        ),
    )

    result = orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=phase,
        selected_task=task,
    )

    assert [item.memory_id for item in result.pack_result.items] == ["sem-fallback"]
    assert result.retrieval_metadata.fallback_used is True
    assert result.retrieval_metadata.fallback_reason == "fts table unavailable"
    assert result.retrieval_metadata.semantic_status == "ready"
