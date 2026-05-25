"""Local semantic index storage and freshness validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engram.db import get_db_connection
from engram.memory_retrieval.semantic_index_contract import (
    SEMANTIC_BUILD_STATUS_SUCCESS,
    SEMANTIC_EMBEDDINGS_FILENAME,
    SEMANTIC_INDEX_ROOT_DIRNAME,
    SEMANTIC_INDEX_SCHEMA_VERSION,
    SEMANTIC_INDEX_SUBDIR,
    SEMANTIC_METADATA_FILENAME,
    SemanticIndexFreshnessSnapshot,
    SemanticIndexMetadata,
    SemanticIndexStatus,
    SemanticIndexStatusResult,
    optional_str,
)


class SemanticIndexStorage:
    """Local filesystem abstraction for project semantic index artifacts."""

    def __init__(self, project_id: str, base_indexes_dir: Path | None = None) -> None:
        self.project_id = project_id
        root = base_indexes_dir or (Path.home() / ".engram" / SEMANTIC_INDEX_ROOT_DIRNAME)
        self.semantic_dir = root / project_id / SEMANTIC_INDEX_SUBDIR
        self.metadata_path = self.semantic_dir / SEMANTIC_METADATA_FILENAME
        self.embeddings_path = self.semantic_dir / SEMANTIC_EMBEDDINGS_FILENAME

    def ensure_storage(self) -> Path:
        """Ensure semantic index directory exists and return its path."""
        self.semantic_dir.mkdir(parents=True, exist_ok=True)
        return self.semantic_dir

    def save_metadata(self, metadata: SemanticIndexMetadata) -> Path:
        """Persist semantic metadata.json to local storage."""
        self.ensure_storage()
        with self.metadata_path.open("w", encoding="utf-8") as handle:
            json.dump(metadata.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
        return self.metadata_path

    def save_embeddings(self, embeddings: Any, *, np_module: Any) -> Path:
        """Persist semantic embedding matrix to local storage."""
        self.ensure_storage()
        np_module.save(self.embeddings_path, embeddings)
        return self.embeddings_path

    def load_metadata(self) -> SemanticIndexMetadata | None:
        """Load semantic metadata if present, otherwise return None."""
        if not self.metadata_path.exists():
            return None
        try:
            with self.metadata_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"failed reading semantic metadata: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("semantic metadata payload must be a JSON object")
        return SemanticIndexMetadata.from_dict(payload)

    def fetch_freshness_snapshot(self) -> SemanticIndexFreshnessSnapshot:
        """Compute memory count and timestamp watermark for freshness checks."""
        conn = get_db_connection()
        try:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS memory_count,
                    MAX(COALESCE(updated_at, created_at)) AS max_updated_at
                FROM memories
                WHERE project_id = ?
                """,
                (self.project_id,),
            ).fetchone()
        finally:
            conn.close()

        return SemanticIndexFreshnessSnapshot(
            project_id=self.project_id,
            memory_count=int(row["memory_count"]),
            max_updated_at=optional_str(row["max_updated_at"]),
        )

    def get_index_status(
        self,
        *,
        expected_model_name: str | None,
        expected_model_dim: int | None,
        expected_schema_version: int = SEMANTIC_INDEX_SCHEMA_VERSION,
    ) -> SemanticIndexStatusResult:
        """Validate semantic artifacts and return deterministic status."""
        metadata_exists = self.metadata_path.exists()
        embeddings_exists = self.embeddings_path.exists()
        if not metadata_exists and not embeddings_exists:
            return SemanticIndexStatusResult(
                SemanticIndexStatus.MISSING, "semantic index artifacts are missing"
            )
        if not metadata_exists:
            return SemanticIndexStatusResult(
                SemanticIndexStatus.MISSING, "semantic metadata is missing"
            )

        metadata = self._safe_load_metadata_for_status()
        if not embeddings_exists:
            return SemanticIndexStatusResult(
                SemanticIndexStatus.MISSING,
                "semantic embeddings artifact is missing",
                metadata=metadata,
            )
        if metadata is None:
            return SemanticIndexStatusResult(
                SemanticIndexStatus.ERROR, "semantic metadata is unreadable"
            )
        if metadata.build_status.casefold() != SEMANTIC_BUILD_STATUS_SUCCESS:
            return SemanticIndexStatusResult(
                SemanticIndexStatus.ERROR,
                f"semantic index build status is '{metadata.build_status}'",
                metadata=metadata,
            )
        if metadata.schema_version != expected_schema_version:
            return SemanticIndexStatusResult(
                SemanticIndexStatus.INCOMPATIBLE,
                "semantic schema version does not match",
                metadata=metadata,
            )
        if expected_model_name is not None and metadata.model_name != expected_model_name:
            return SemanticIndexStatusResult(
                SemanticIndexStatus.INCOMPATIBLE,
                "semantic model name does not match",
                metadata=metadata,
            )
        if expected_model_dim is not None and metadata.model_dim != expected_model_dim:
            return SemanticIndexStatusResult(
                SemanticIndexStatus.INCOMPATIBLE,
                "semantic model dimension does not match",
                metadata=metadata,
            )

        current_snapshot = self.fetch_freshness_snapshot()
        if metadata.indexed_memory_count != current_snapshot.memory_count:
            return SemanticIndexStatusResult(
                SemanticIndexStatus.STALE,
                "semantic index memory count watermark is stale",
                metadata=metadata,
                current_snapshot=current_snapshot,
            )
        if metadata.indexed_max_updated_at != current_snapshot.max_updated_at:
            return SemanticIndexStatusResult(
                SemanticIndexStatus.STALE,
                "semantic index timestamp watermark is stale",
                metadata=metadata,
                current_snapshot=current_snapshot,
            )
        return SemanticIndexStatusResult(
            SemanticIndexStatus.READY,
            "semantic index is ready",
            metadata=metadata,
            current_snapshot=current_snapshot,
        )

    def _safe_load_metadata_for_status(self) -> SemanticIndexMetadata | None:
        """Load metadata for status checks, returning None when invalid."""
        try:
            return self.load_metadata()
        except ValueError:
            return None
