"""Tests for local semantic index storage and semantic retrieval fallback behavior."""

import json

from engram.memory_retrieval import (
    SEMANTIC_BUILD_STATUS_SUCCESS,
    SemanticIndexMetadata,
    SemanticIndexStatus,
    SemanticIndexStorage,
)
from engram.memory_retrieval.fts_retriever import retrieve_task_memory_semantic_candidates
from engram.memory_retrieval.query_builder import RetrievalQueryMetadata, TaskRetrievalQuery
from engram.models.memory import Memory
from engram.models.task import Task


def _metadata(
    *,
    project_id: str,
    indexed_memory_count: int,
    indexed_max_updated_at: str | None,
    model_name: str = "BAAI/bge-small-en-v1.5",
    model_dim: int = 384,
) -> SemanticIndexMetadata:
    return SemanticIndexMetadata(
        schema_version=1,
        project_id=project_id,
        model_name=model_name,
        model_dim=model_dim,
        indexed_memory_count=indexed_memory_count,
        indexed_max_updated_at=indexed_max_updated_at,
        build_started_at="2026-05-25T10:00:00Z",
        build_completed_at="2026-05-25T10:00:10Z",
        build_status=SEMANTIC_BUILD_STATUS_SUCCESS,
        memory_ids=(),
        source_hash="abc123",
        source_version="v1",
    )


def test_semantic_storage_initialization_creates_local_directory(project, tmp_path) -> None:
    indexes_dir = tmp_path / "indexes"
    storage = SemanticIndexStorage(project.id, base_indexes_dir=indexes_dir)

    assert storage.semantic_dir == indexes_dir / project.id / "semantic"
    assert storage.metadata_path == storage.semantic_dir / "metadata.json"
    assert storage.embeddings_path == storage.semantic_dir / "embeddings.npy"
    assert not storage.semantic_dir.exists()

    created_dir = storage.ensure_storage()

    assert created_dir == storage.semantic_dir
    assert storage.semantic_dir.exists()
    assert storage.semantic_dir.is_dir()


def test_semantic_metadata_round_trip_persists_contract_fields(project, tmp_path) -> None:
    storage = SemanticIndexStorage(project.id, base_indexes_dir=tmp_path / "indexes")
    metadata = _metadata(
        project_id=project.id,
        indexed_memory_count=3,
        indexed_max_updated_at="2026-05-25 10:00:00",
    )

    saved_path = storage.save_metadata(metadata)
    loaded = storage.load_metadata()

    assert saved_path == storage.metadata_path
    assert isinstance(loaded, SemanticIndexMetadata)
    assert loaded == metadata


def test_semantic_index_status_is_missing_when_artifacts_do_not_exist(project, tmp_path) -> None:
    storage = SemanticIndexStorage(project.id, base_indexes_dir=tmp_path / "indexes")

    status = storage.get_index_status(
        expected_model_name="BAAI/bge-small-en-v1.5",
        expected_model_dim=384,
    )

    assert status.status == SemanticIndexStatus.MISSING
    assert "missing" in status.reason
    assert status.metadata is None
    assert status.current_snapshot is None


def test_semantic_index_status_is_stale_on_memory_count_mismatch(project, tmp_path) -> None:
    storage = SemanticIndexStorage(project.id, base_indexes_dir=tmp_path / "indexes")
    Memory.create(
        project_id=project.id,
        type="lesson",
        title="One memory",
        content="Memory content",
        scope="task",
    )
    storage.ensure_storage()
    storage.embeddings_path.write_bytes(b"placeholder")
    storage.save_metadata(
        _metadata(
            project_id=project.id,
            indexed_memory_count=0,
            indexed_max_updated_at=None,
        )
    )

    status = storage.get_index_status(
        expected_model_name="BAAI/bge-small-en-v1.5",
        expected_model_dim=384,
    )

    assert status.status == SemanticIndexStatus.STALE
    assert "count" in status.reason
    assert status.metadata is not None
    assert status.current_snapshot is not None
    assert status.current_snapshot.memory_count == 1


def test_semantic_index_status_is_ready_when_watermarks_match(project, tmp_path) -> None:
    storage = SemanticIndexStorage(project.id, base_indexes_dir=tmp_path / "indexes")
    memory = Memory.create(
        project_id=project.id,
        type="lesson",
        title="Ready memory",
        content="Ready content",
        scope="task",
    )
    storage.ensure_storage()
    storage.embeddings_path.write_bytes(b"placeholder")
    snapshot = storage.fetch_freshness_snapshot()
    storage.save_metadata(
        SemanticIndexMetadata(
            schema_version=1,
            project_id=project.id,
            model_name="BAAI/bge-small-en-v1.5",
            model_dim=384,
            indexed_memory_count=snapshot.memory_count,
            indexed_max_updated_at=snapshot.max_updated_at,
            build_started_at="2026-05-25T10:00:00Z",
            build_completed_at="2026-05-25T10:00:10Z",
            build_status=SEMANTIC_BUILD_STATUS_SUCCESS,
            memory_ids=(memory.id,),
            source_hash="hash-ready",
            source_version="v1",
        )
    )

    status = storage.get_index_status(
        expected_model_name="BAAI/bge-small-en-v1.5",
        expected_model_dim=384,
    )

    assert status.status == SemanticIndexStatus.READY
    assert status.reason == "semantic index is ready"
    assert status.metadata is not None
    assert status.current_snapshot is not None


class _FakeMatrix:
    def __init__(self, rows: list[list[float]]) -> None:
        self._rows = rows
        width = len(rows[0]) if rows else 0
        self.shape = (len(rows), width)

    def __getitem__(self, index: int) -> list[float]:
        return self._rows[index]


class _FakeNumpy:
    float32 = float

    @staticmethod
    def asarray(values: list[float], dtype: object = None) -> list[float]:
        del dtype
        return [float(value) for value in values]

    @staticmethod
    def save(path, embeddings: _FakeMatrix) -> None:
        rows = [embeddings[row] for row in range(embeddings.shape[0])]
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"rows": rows}, handle)

    @staticmethod
    def load(path, allow_pickle: bool = False) -> _FakeMatrix:
        del allow_pickle
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
        return _FakeMatrix([[float(item) for item in row] for row in payload["rows"]])


class _FakeTextEmbedding:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def embed(self, texts: list[str]):
        for text in texts:
            lowered = text.casefold()
            if "release" in lowered:
                yield [1.0, 0.0, 0.0]
            elif "docs" in lowered:
                yield [0.0, 1.0, 0.0]
            else:
                yield [0.0, 0.0, 1.0]


def _build_query(*, project_id: str, task_id: str, query_text: str) -> TaskRetrievalQuery:
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


def _write_ready_semantic_index(
    *,
    storage: SemanticIndexStorage,
    project_id: str,
    memory_ids: tuple[str, ...],
    embedding_rows: list[list[float]],
) -> None:
    storage.ensure_storage()
    storage.save_embeddings(_FakeMatrix(embedding_rows), np_module=_FakeNumpy)
    snapshot = storage.fetch_freshness_snapshot()
    storage.save_metadata(
        SemanticIndexMetadata(
            schema_version=1,
            project_id=project_id,
            model_name="BAAI/bge-small-en-v1.5",
            model_dim=3,
            indexed_memory_count=snapshot.memory_count,
            indexed_max_updated_at=snapshot.max_updated_at,
            build_started_at="2026-05-25T10:00:00Z",
            build_completed_at="2026-05-25T10:00:10Z",
            build_status=SEMANTIC_BUILD_STATUS_SUCCESS,
            memory_ids=memory_ids,
            source_hash="semantic-hash",
            source_version="v1",
        )
    )


def test_semantic_retriever_returns_similarity_ranked_eligible_candidates(
    project, tmp_path, monkeypatch
) -> None:
    task = Task.create(project_id=project.id, title="Prepare release docs")
    task_candidate = Memory.create(
        project_id=project.id,
        type="lesson",
        title="Release docs checklist",
        content="Include release notes and docs updates.",
        scope="task",
        task_id=task.id,
    )
    project_candidate = Memory.create(
        project_id=project.id,
        type="decision",
        title="Public docs decisions",
        content="Public docs should mirror command output.",
        scope="project",
        level="L2",
    )
    guardrail = Memory.create(
        project_id=project.id,
        type="constraint",
        title="Release identity guardrail",
        content="This should not appear in semantic candidates.",
        scope="project",
        level="L1",
    )
    storage = SemanticIndexStorage(project.id, base_indexes_dir=tmp_path / "indexes")
    _write_ready_semantic_index(
        storage=storage,
        project_id=project.id,
        memory_ids=(task_candidate.id, project_candidate.id, guardrail.id),
        embedding_rows=[[0.95, 0.05, 0.0], [0.85, 0.15, 0.0], [1.0, 0.0, 0.0]],
    )
    monkeypatch.setattr(
        "engram.memory_retrieval.fts_retriever.semantic.load_semantic_embedding_dependencies",
        lambda: (_FakeNumpy, _FakeTextEmbedding),
    )

    result = retrieve_task_memory_semantic_candidates(
        _build_query(project_id=project.id, task_id=task.id, query_text="release docs"),
        semantic_storage=storage,
    )

    assert [candidate.memory_id for candidate in result.candidates] == [
        task_candidate.id,
        project_candidate.id,
    ]
    assert guardrail.id not in [candidate.memory_id for candidate in result.candidates]
    assert all(candidate.retrieval_source == "semantic" for candidate in result.candidates)
    assert result.metadata.fallback_used is False
    assert result.metadata.returned_task_scope_candidate_count == 1
    assert result.metadata.returned_project_scope_candidate_count == 1


def test_semantic_retriever_empty_ready_index_returns_no_candidates(project, tmp_path, monkeypatch):
    task = Task.create(project_id=project.id, title="No indexed memories yet")
    storage = SemanticIndexStorage(project.id, base_indexes_dir=tmp_path / "indexes")
    _write_ready_semantic_index(
        storage=storage,
        project_id=project.id,
        memory_ids=(),
        embedding_rows=[],
    )
    monkeypatch.setattr(
        "engram.memory_retrieval.fts_retriever.semantic.load_semantic_embedding_dependencies",
        lambda: (_FakeNumpy, _FakeTextEmbedding),
    )

    result = retrieve_task_memory_semantic_candidates(
        _build_query(project_id=project.id, task_id=task.id, query_text="release docs"),
        semantic_storage=storage,
    )

    assert result.candidates == ()
    assert result.metadata.fallback_used is False
    assert result.metadata.scanned_row_count == 0


def test_semantic_retriever_missing_stale_and_error_indexes_return_fallback(
    project, tmp_path
) -> None:
    task = Task.create(project_id=project.id, title="Semantic fallback checks")
    query = _build_query(project_id=project.id, task_id=task.id, query_text="release")

    missing_storage = SemanticIndexStorage(project.id, base_indexes_dir=tmp_path / "missing")
    missing_result = retrieve_task_memory_semantic_candidates(
        query,
        semantic_storage=missing_storage,
    )
    assert missing_result.candidates == ()
    assert missing_result.metadata.fallback_used is True
    assert "semantic index missing" in str(missing_result.metadata.fallback_reason)

    Memory.create(
        project_id=project.id,
        type="lesson",
        title="New memory",
        content="Ensures stale watermark mismatch.",
        scope="task",
        task_id=task.id,
    )
    stale_storage = SemanticIndexStorage(project.id, base_indexes_dir=tmp_path / "stale")
    stale_storage.ensure_storage()
    stale_storage.save_embeddings(_FakeMatrix([[1.0, 0.0, 0.0]]), np_module=_FakeNumpy)
    stale_storage.save_metadata(
        SemanticIndexMetadata(
            schema_version=1,
            project_id=project.id,
            model_name="BAAI/bge-small-en-v1.5",
            model_dim=3,
            indexed_memory_count=0,
            indexed_max_updated_at=None,
            build_started_at="2026-05-25T10:00:00Z",
            build_completed_at="2026-05-25T10:00:10Z",
            build_status=SEMANTIC_BUILD_STATUS_SUCCESS,
            memory_ids=(),
            source_hash="stale-hash",
            source_version="v1",
        )
    )
    stale_result = retrieve_task_memory_semantic_candidates(query, semantic_storage=stale_storage)
    assert stale_result.candidates == ()
    assert stale_result.metadata.fallback_used is True
    assert "semantic index stale" in str(stale_result.metadata.fallback_reason)

    error_storage = SemanticIndexStorage(project.id, base_indexes_dir=tmp_path / "error")
    error_storage.ensure_storage()
    error_storage.save_embeddings(_FakeMatrix([]), np_module=_FakeNumpy)
    error_storage.metadata_path.write_text("{ bad-json", encoding="utf-8")
    error_result = retrieve_task_memory_semantic_candidates(query, semantic_storage=error_storage)
    assert error_result.candidates == ()
    assert error_result.metadata.fallback_used is True
    assert "semantic index error" in str(error_result.metadata.fallback_reason)
