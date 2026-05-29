"""Semantic retrieval over task memories and eligible project guidance candidates."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from engram.memory_retrieval.fts_retriever.scoring import (
    _cosine_similarity,
    _is_semantic_eligible,
    build_retrieval_metadata,
)
from engram.memory_retrieval.query_builder import TaskRetrievalQuery
from engram.memory_retrieval.retrieval_contract import (
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


def _make_semantic_meta(
    project_id: str,
    task_id: str,
    query_text: str,
    max_candidates: int,
    **kwargs: Any,
) -> TaskMemoryRetrievalMetadata:
    """Build semantic retrieval metadata with defaults."""
    base = {
        "project_id": project_id,
        "query_task_id": task_id,
        "source": "semantic",
        "requested_query_text": query_text,
        "normalized_fts_query": "",
        "query_term_count": 0,
        "query_was_empty": False,
        "fallback_used": False,
        "fallback_reason": None,
        "max_candidates": max_candidates,
        "scanned_row_count": 0,
        "returned_candidate_count": 0,
        "scanned_task_scope_row_count": 0,
        "scanned_project_scope_row_count": 0,
        "returned_task_scope_candidate_count": 0,
        "returned_project_scope_candidate_count": 0,
    }
    base.update(kwargs)
    return build_retrieval_metadata(**base)


def retrieve_task_memory_semantic_candidates(
    retrieval_query: TaskRetrievalQuery,
    options: TaskMemoryRetrievalOptions | None = None,
    *,
    semantic_storage: SemanticIndexStorage | None = None,
    model_name: str = DEFAULT_SEMANTIC_MODEL_NAME,
) -> TaskMemoryRetrievalResult:
    """Retrieve semantic candidates from local embedding artifacts."""
    resolved = options or TaskMemoryRetrievalOptions()
    project_id = retrieval_query.metadata.project_id
    task_id = retrieval_query.metadata.task_id
    query_text = retrieval_query.query_text.strip()

    if not query_text:
        meta = _make_semantic_meta(
            project_id,
            task_id,
            retrieval_query.query_text,
            resolved.max_candidates,
            query_was_empty=True,
        )
        return TaskMemoryRetrievalResult(candidates=(), metadata=meta)

    storage = semantic_storage or SemanticIndexStorage(project_id)
    status = storage.get_index_status(expected_model_name=model_name, expected_model_dim=None)
    if status.status != SemanticIndexStatus.READY or status.metadata is None:
        reason = (
            f"semantic index {status.status.value}: {status.reason}"
            if status.status != SemanticIndexStatus.READY
            else "missing metadata"
        )
        meta = _make_semantic_meta(
            project_id,
            task_id,
            retrieval_query.query_text,
            resolved.max_candidates,
            fallback_used=True,
            fallback_reason=reason,
        )
        return TaskMemoryRetrievalResult(candidates=(), metadata=meta)

    try:

        def _to_float_tuple(vector: Iterable[object]) -> tuple[float, ...]:
            return tuple(float(value) for value in vector)

        def _list_project_memories(project_id: str) -> list[Any]:
            from engram.models.memory import Memory

            return Memory.list_by_project(project_id)

        def _semantic_candidate_from_memory(
            memory: Any, similarity: float, query_task_id: str
        ) -> TaskMemoryCandidate:
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

        np_module, text_embedding_cls = load_semantic_embedding_dependencies()
        raw_matrix: Any = np_module.load(storage.embeddings_path, allow_pickle=False)
        matrix_shape = getattr(raw_matrix, "shape", None)
        if (
            not isinstance(matrix_shape, tuple)
            or len(matrix_shape) != 2
            or matrix_shape[0] != len(status.metadata.memory_ids)
        ):
            raise ValueError("Invalid embeddings matrix shape or mismatched memory ids count")

        embedder = text_embedding_cls(model_name=model_name)
        query_vectors = list(embedder.embed([query_text]))
        if not query_vectors:
            raise ValueError("semantic embedder returned no query vectors")
        query_vector = _to_float_tuple(np_module.asarray(query_vectors[0], dtype=np_module.float32))

        eligible = {m.id: m for m in _list_project_memories(project_id) if _is_semantic_eligible(m)}
        scored: list[tuple[float, TaskMemoryCandidate]] = []
        for index, mem_id in enumerate(status.metadata.memory_ids):
            memory = eligible.get(mem_id)
            if memory is not None:
                sim = _cosine_similarity(query_vector, _to_float_tuple(raw_matrix[index]))
                scored.append((sim, _semantic_candidate_from_memory(memory, sim, task_id)))

        ordered = tuple(
            cand
            for _, cand in sorted(scored, key=lambda x: (-x[0], x[1].memory_id))[
                : resolved.max_candidates
            ]
        )
        meta = _make_semantic_meta(
            project_id,
            task_id,
            retrieval_query.query_text,
            resolved.max_candidates,
            scanned_row_count=matrix_shape[0],
            returned_candidate_count=len(ordered),
            scanned_task_scope_row_count=sum(1 for m in eligible.values() if m.scope == "task"),
            scanned_project_scope_row_count=sum(
                1 for m in eligible.values() if m.scope == "project"
            ),
            returned_task_scope_candidate_count=sum(1 for c in ordered if c.scope == "task"),
            returned_project_scope_candidate_count=sum(1 for c in ordered if c.scope == "project"),
        )
        return TaskMemoryRetrievalResult(candidates=ordered, metadata=meta)
    except Exception as exc:
        meta = _make_semantic_meta(
            project_id,
            task_id,
            retrieval_query.query_text,
            resolved.max_candidates,
            fallback_used=True,
            fallback_reason=f"semantic retrieval failed: {exc}",
        )
        return TaskMemoryRetrievalResult(candidates=(), metadata=meta)
