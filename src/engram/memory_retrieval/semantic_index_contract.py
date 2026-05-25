"""Contracts shared by semantic index storage and retrieval integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

SEMANTIC_INDEX_SCHEMA_VERSION = 1
SEMANTIC_INDEX_ROOT_DIRNAME = "indexes"
SEMANTIC_INDEX_SUBDIR = "semantic"
SEMANTIC_METADATA_FILENAME = "metadata.json"
SEMANTIC_EMBEDDINGS_FILENAME = "embeddings.npy"
SEMANTIC_BUILD_STATUS_SUCCESS = "success"
DEFAULT_SEMANTIC_MODEL_NAME = "BAAI/bge-small-en-v1.5"
KNOWN_MODEL_DIMENSIONS = {"BAAI/bge-small-en-v1.5": 384}


class SemanticIndexStatus(str, Enum):
    """Deterministic semantic index readiness states."""

    READY = "ready"
    MISSING = "missing"
    STALE = "stale"
    INCOMPATIBLE = "incompatible"
    ERROR = "error"


@dataclass(frozen=True)
class SemanticIndexFreshnessSnapshot:
    """Current memory-table freshness watermark used for index validation."""

    project_id: str
    memory_count: int
    max_updated_at: str | None


@dataclass(frozen=True)
class SemanticIndexMetadata:
    """Persisted semantic index metadata contract."""

    schema_version: int
    project_id: str
    model_name: str
    model_dim: int
    indexed_memory_count: int
    indexed_max_updated_at: str | None
    build_started_at: str
    build_completed_at: str | None
    build_status: str
    memory_ids: tuple[str, ...] = ()
    source_hash: str | None = None
    source_version: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize metadata to a JSON-safe dictionary."""
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "model_name": self.model_name,
            "model_dim": self.model_dim,
            "indexed_memory_count": self.indexed_memory_count,
            "indexed_max_updated_at": self.indexed_max_updated_at,
            "build_started_at": self.build_started_at,
            "build_completed_at": self.build_completed_at,
            "build_status": self.build_status,
            "memory_ids": list(self.memory_ids),
            "source_hash": self.source_hash,
            "source_version": self.source_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> SemanticIndexMetadata:
        """Deserialize metadata from dictionary values."""
        required_fields = (
            "schema_version",
            "project_id",
            "model_name",
            "model_dim",
            "indexed_memory_count",
            "build_started_at",
            "build_status",
        )
        missing_fields = [field for field in required_fields if field not in payload]
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"semantic metadata missing required fields: {missing}")

        raw_memory_ids = payload.get("memory_ids", ())
        if raw_memory_ids is None:
            memory_ids: tuple[str, ...] = ()
        elif isinstance(raw_memory_ids, list):
            memory_ids = tuple(str(item) for item in raw_memory_ids)
        else:
            raise ValueError("semantic metadata field 'memory_ids' must be a list")

        return cls(
            schema_version=int(payload["schema_version"]),
            project_id=str(payload["project_id"]),
            model_name=str(payload["model_name"]),
            model_dim=int(payload["model_dim"]),
            indexed_memory_count=int(payload["indexed_memory_count"]),
            indexed_max_updated_at=optional_str(payload.get("indexed_max_updated_at")),
            build_started_at=str(payload["build_started_at"]),
            build_completed_at=optional_str(payload.get("build_completed_at")),
            build_status=str(payload["build_status"]),
            memory_ids=memory_ids,
            source_hash=optional_str(payload.get("source_hash")),
            source_version=optional_str(payload.get("source_version")),
        )


@dataclass(frozen=True)
class SemanticIndexStatusResult:
    """Semantic index status plus reason and optional supporting metadata."""

    status: SemanticIndexStatus
    reason: str
    metadata: SemanticIndexMetadata | None = None
    current_snapshot: SemanticIndexFreshnessSnapshot | None = None


class SemanticReindexError(RuntimeError):
    """Raised when semantic reindex cannot complete safely."""


@dataclass(frozen=True)
class SemanticReindexResult:
    """Summary for semantic index rebuild command output."""

    scanned_count: int
    indexed_count: int
    skipped_count: int
    failed_count: int
    stale_count: int
    model_name: str
    model_dim: int
    metadata_path: str
    embeddings_path: str
    status_before: str


def load_semantic_embedding_dependencies() -> tuple[Any, Any]:
    """Load optional semantic dependencies only when reindex is invoked."""
    missing: list[str] = []
    np_module: Any | None = None
    text_embedding_cls: Any | None = None
    try:
        import numpy as np_module  # type: ignore[no-redef]
    except ModuleNotFoundError:
        missing.append("numpy")
    try:
        from fastembed import TextEmbedding as text_embedding_cls  # type: ignore[no-redef]
    except ModuleNotFoundError:
        missing.append("fastembed")
    if missing:
        joined = ", ".join(sorted(missing))
        raise SemanticReindexError(
            f"missing optional semantic dependencies: {joined}. "
            "Install with: uv pip install 'fastembed>=0.8,<1' 'numpy>=2,<3'"
        )
    return np_module, text_embedding_cls


def resolve_semantic_model_dim(
    *, model_name: str, text_embedding_cls: Any, fallback_dim: int | None
) -> int:
    """Resolve embedding dimension for semantic metadata."""
    resolver = getattr(text_embedding_cls, "get_embedding_size", None)
    if callable(resolver):
        try:
            return int(resolver(model_name))
        except Exception:
            pass
    return (
        int(fallback_dim) if fallback_dim is not None else KNOWN_MODEL_DIMENSIONS.get(model_name, 0)
    )


def optional_str(value: object) -> str | None:
    """Return normalized optional string values."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
