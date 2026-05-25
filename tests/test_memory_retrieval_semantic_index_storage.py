"""Tests for local semantic index storage and freshness state handling."""

from engram.memory_retrieval import (
    SEMANTIC_BUILD_STATUS_SUCCESS,
    SemanticIndexMetadata,
    SemanticIndexStatus,
    SemanticIndexStorage,
)
from engram.models.memory import Memory


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
