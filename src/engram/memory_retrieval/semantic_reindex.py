from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from engram.memory_retrieval.semantic_index_contract import (
    DEFAULT_SEMANTIC_MODEL_NAME,
    KNOWN_MODEL_DIMENSIONS,
    SEMANTIC_BUILD_STATUS_SUCCESS,
    SEMANTIC_INDEX_SCHEMA_VERSION,
    SemanticIndexMetadata,
    SemanticIndexStatus,
    SemanticReindexError,
    SemanticReindexResult,
    load_semantic_embedding_dependencies,
    resolve_semantic_model_dim,
)
from engram.memory_retrieval.semantic_index_storage import SemanticIndexStorage
from engram.models.memory import Memory


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _embedding_text(memory: Memory) -> str:
    tags = ", ".join(tag for tag in memory.tags if tag)
    parts = [f"title: {memory.title}", f"type: {memory.type}", f"scope: {memory.scope}"]
    if memory.level:
        parts.append(f"level: {memory.level}")
    if memory.task_id:
        parts.append(f"task_id: {memory.task_id}")
    if tags:
        parts.append(f"tags: {tags}")
    parts.append(f"content: {memory.content}")
    return "\n".join(parts)


def _make_result(
    storage: SemanticIndexStorage,
    status_before: SemanticIndexStatus,
    scanned_count: int,
    indexed_count: int,
    skipped_count: int,
    failed_count: int,
    stale_count: int,
    model_name: str,
    model_dim: int,
) -> SemanticReindexResult:
    return SemanticReindexResult(
        scanned_count,
        indexed_count,
        skipped_count,
        failed_count,
        stale_count,
        model_name,
        model_dim,
        str(storage.metadata_path),
        str(storage.embeddings_path),
        status_before.value,
    )


def reindex_semantic_memory_index(
    *,
    project_id: str,
    semantic_storage: SemanticIndexStorage | None = None,
    model_name: str = DEFAULT_SEMANTIC_MODEL_NAME,
    full: bool = False,
    task_scope_only: bool = False,
    force: bool = False,
) -> SemanticReindexResult:
    storage = semantic_storage or SemanticIndexStorage(project_id)
    status_before_result = storage.get_index_status(
        expected_model_name=model_name, expected_model_dim=None
    )
    status_before = status_before_result.status
    memories = Memory.list_by_project(project_id)
    if task_scope_only:
        memories = [memory for memory in memories if memory.scope == "task"]
    memories = sorted(memories, key=lambda item: item.id)
    scanned_count = len(memories)
    if (
        not full
        and not force
        and status_before == SemanticIndexStatus.READY
        and status_before_result.metadata is not None
    ):
        metadata = status_before_result.metadata
        return _make_result(
            storage,
            status_before,
            scanned_count,
            0,
            scanned_count,
            0,
            0,
            metadata.model_name,
            metadata.model_dim,
        )

    stale_count = scanned_count if status_before == SemanticIndexStatus.STALE else 0
    build_started_at = _timestamp()
    if not memories:
        model_dim = KNOWN_MODEL_DIMENSIONS.get(model_name, 0)
        storage.ensure_storage()
        storage.embeddings_path.write_bytes(b"")
        snapshot = storage.fetch_freshness_snapshot()
        storage.save_metadata(
            SemanticIndexMetadata(
                schema_version=SEMANTIC_INDEX_SCHEMA_VERSION,
                project_id=project_id,
                model_name=model_name,
                model_dim=model_dim,
                indexed_memory_count=0,
                indexed_max_updated_at=snapshot.max_updated_at,
                build_started_at=build_started_at,
                build_completed_at=_timestamp(),
                build_status=SEMANTIC_BUILD_STATUS_SUCCESS,
                memory_ids=(),
                source_hash=None,
                source_version="v1",
            )
        )
        return _make_result(storage, status_before, 0, 0, 0, 0, stale_count, model_name, model_dim)

    np_module, text_embedding_cls = load_semantic_embedding_dependencies()
    embedder = text_embedding_cls(model_name=model_name)
    vectors: list[Any] = []
    indexed_ids: list[str] = []
    failed_count = 0

    try:
        texts = [_embedding_text(memory) for memory in memories]
        raw_vectors_batch = list(embedder.embed(texts))
        if len(raw_vectors_batch) != len(memories):
            raise SemanticReindexError("embedder returned incorrect number of vectors")
        for memory, raw_vector in zip(memories, raw_vectors_batch, strict=True):
            vector = np_module.asarray(raw_vector, dtype=np_module.float32)
            if getattr(vector, "ndim", 1) != 1:
                raise SemanticReindexError("embedder returned a non-1D vector")
            vectors.append(vector)
            indexed_ids.append(memory.id)
    except Exception:
        vectors.clear()
        indexed_ids.clear()
        failed_count = 0
        for memory in memories:
            try:
                raw_vectors = list(embedder.embed([_embedding_text(memory)]))
                if not raw_vectors:
                    raise SemanticReindexError("embedder returned no vectors")
                vector = np_module.asarray(raw_vectors[0], dtype=np_module.float32)
                if getattr(vector, "ndim", 1) != 1:
                    raise SemanticReindexError("embedder returned a non-1D vector")
                vectors.append(vector)
                indexed_ids.append(memory.id)
            except Exception:
                failed_count += 1
    if vectors:
        matrix = np_module.stack(vectors).astype(np_module.float32)
        model_dim = resolve_semantic_model_dim(
            model_name=model_name,
            text_embedding_cls=text_embedding_cls,
            fallback_dim=int(matrix.shape[1]),
        )
    else:
        model_dim = resolve_semantic_model_dim(
            model_name=model_name,
            text_embedding_cls=text_embedding_cls,
            fallback_dim=None,
        )
        matrix = np_module.zeros((0, model_dim), dtype=np_module.float32)

    snapshot = storage.fetch_freshness_snapshot()
    try:
        storage.save_embeddings(matrix, np_module=np_module)
        source_hash = hashlib.sha256()
        for memory_id in indexed_ids:
            source_hash.update(memory_id.encode())
            source_hash.update(b"\n")
        storage.save_metadata(
            SemanticIndexMetadata(
                schema_version=SEMANTIC_INDEX_SCHEMA_VERSION,
                project_id=project_id,
                model_name=model_name,
                model_dim=model_dim,
                indexed_memory_count=snapshot.memory_count,
                indexed_max_updated_at=snapshot.max_updated_at,
                build_started_at=build_started_at,
                build_completed_at=_timestamp(),
                build_status=SEMANTIC_BUILD_STATUS_SUCCESS,
                memory_ids=tuple(indexed_ids),
                source_hash=source_hash.hexdigest() if indexed_ids else None,
                source_version="v1",
            )
        )
    except OSError as exc:
        raise SemanticReindexError(f"failed writing semantic index artifacts: {exc}") from exc
    indexed_count = len(indexed_ids)
    skipped_count = max(scanned_count - indexed_count - failed_count, 0)
    return _make_result(
        storage,
        status_before,
        scanned_count,
        indexed_count,
        skipped_count,
        failed_count,
        stale_count,
        model_name,
        model_dim,
    )
