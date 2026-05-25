"""Tests for semantic memory reindex pipeline behavior."""

import pytest

from engram.memory_retrieval.semantic_index_storage import SemanticIndexStorage
from engram.memory_retrieval.semantic_reindex import (
    SemanticReindexError,
    reindex_semantic_memory_index,
)
from engram.models.memory import Memory


class _FakeVector:
    def __init__(self, values: list[float]) -> None:
        self.values = values
        self.ndim = 1

    def __len__(self) -> int:
        return len(self.values)


class _FakeMatrix:
    def __init__(self, row_count: int, col_count: int) -> None:
        self.shape = (row_count, col_count)

    def astype(self, _dtype: object) -> "_FakeMatrix":
        return self


class _FakeNumpy:
    float32 = float

    @staticmethod
    def asarray(values: list[float], dtype: object = None) -> _FakeVector:
        del dtype
        return _FakeVector([float(item) for item in values])

    @staticmethod
    def stack(vectors: list[_FakeVector]) -> _FakeMatrix:
        if not vectors:
            return _FakeMatrix(0, 0)
        return _FakeMatrix(len(vectors), len(vectors[0]))

    @staticmethod
    def zeros(shape: tuple[int, int], dtype: object = None) -> _FakeMatrix:
        del dtype
        return _FakeMatrix(shape[0], shape[1])

    @staticmethod
    def save(path, matrix: _FakeMatrix) -> None:
        with open(path, "wb") as handle:
            handle.write(f"{matrix.shape[0]}x{matrix.shape[1]}".encode())


class _FakeTextEmbedding:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def embed(self, texts: list[str]):
        for text in texts:
            if "FAIL_EMBED" in text:
                raise RuntimeError("embed failure")
            yield [0.1, 0.2, 0.3]

    @staticmethod
    def get_embedding_size(_model_name: str) -> int:
        return 3


def test_semantic_reindex_success_writes_embeddings_and_metadata(
    tmp_db, project, monkeypatch, tmp_path
) -> None:
    Memory.create(
        project_id=project.id,
        type="lesson",
        title="Memory one",
        content="First content",
        scope="task",
    )
    Memory.create(
        project_id=project.id,
        type="decision",
        title="Memory two",
        content="Second content",
        scope="project",
        level="L2",
    )

    monkeypatch.setattr(
        "engram.memory_retrieval.semantic_reindex.load_semantic_embedding_dependencies",
        lambda: (_FakeNumpy, _FakeTextEmbedding),
    )
    storage = SemanticIndexStorage(project.id, base_indexes_dir=tmp_path / "indexes")

    result = reindex_semantic_memory_index(
        project_id=project.id,
        semantic_storage=storage,
        force=True,
    )

    assert result.scanned_count == 2
    assert result.indexed_count == 2
    assert result.skipped_count == 0
    assert result.failed_count == 0
    assert storage.embeddings_path.exists()
    metadata = storage.load_metadata()
    assert metadata is not None
    assert metadata.project_id == project.id
    assert metadata.memory_ids == tuple(sorted(metadata.memory_ids))


def test_semantic_reindex_no_memory_succeeds_without_optional_dependencies(
    tmp_db, project, tmp_path
) -> None:
    storage = SemanticIndexStorage(project.id, base_indexes_dir=tmp_path / "indexes")

    result = reindex_semantic_memory_index(
        project_id=project.id,
        semantic_storage=storage,
        force=True,
    )

    assert result.scanned_count == 0
    assert result.indexed_count == 0
    assert result.skipped_count == 0
    assert result.failed_count == 0
    assert storage.embeddings_path.exists()
    metadata = storage.load_metadata()
    assert metadata is not None
    assert metadata.indexed_memory_count == 0


def test_semantic_reindex_dependency_failure_surfaces_clear_error(
    tmp_db, project, monkeypatch, tmp_path
) -> None:
    Memory.create(
        project_id=project.id,
        type="lesson",
        title="Need embed",
        content="content",
        scope="task",
    )
    storage = SemanticIndexStorage(project.id, base_indexes_dir=tmp_path / "indexes")

    def _raise_dependency_error() -> tuple[object, object]:
        raise SemanticReindexError("missing optional semantic dependencies: fastembed")

    monkeypatch.setattr(
        "engram.memory_retrieval.semantic_reindex.load_semantic_embedding_dependencies",
        _raise_dependency_error,
    )

    with pytest.raises(SemanticReindexError, match="missing optional semantic dependencies"):
        reindex_semantic_memory_index(project_id=project.id, semantic_storage=storage, force=True)


def test_semantic_reindex_index_write_failure_surfaces_clear_error(
    tmp_db, project, monkeypatch, tmp_path
) -> None:
    Memory.create(
        project_id=project.id,
        type="lesson",
        title="Write fail",
        content="content",
        scope="task",
    )
    monkeypatch.setattr(
        "engram.memory_retrieval.semantic_reindex.load_semantic_embedding_dependencies",
        lambda: (_FakeNumpy, _FakeTextEmbedding),
    )
    storage = SemanticIndexStorage(project.id, base_indexes_dir=tmp_path / "indexes")

    def _raise_write_error(*args, **kwargs) -> None:
        del args, kwargs
        raise OSError("disk unavailable")

    monkeypatch.setattr(storage, "save_embeddings", _raise_write_error)

    with pytest.raises(SemanticReindexError, match="failed writing semantic index artifacts"):
        reindex_semantic_memory_index(project_id=project.id, semantic_storage=storage, force=True)
