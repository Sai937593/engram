"""Memory retrieval helpers shared across startup and CLI flows."""

from engram.memory_retrieval.fts_query import normalize_fts_query_text
from engram.memory_retrieval.fts_retriever import (
    TaskMemoryCandidate,
    TaskMemoryRetrievalMetadata,
    TaskMemoryRetrievalOptions,
    TaskMemoryRetrievalResult,
    retrieve_task_memory_candidates,
    retrieve_task_memory_semantic_candidates,
)
from engram.memory_retrieval.pack_contract import (
    TaskMemoryPackedItem,
    TaskMemoryPackMetadata,
    TaskMemoryPackOptions,
    TaskMemoryPackResult,
    pack_task_memories,
    resolve_task_memory_pack_options,
)
from engram.memory_retrieval.query_builder import (
    RetrievalQueryBuilderOptions,
    RetrievalQueryMetadata,
    TaskRetrievalQuery,
    build_task_retrieval_query,
)
from engram.memory_retrieval.semantic_index_contract import (
    SEMANTIC_BUILD_STATUS_SUCCESS,
    SEMANTIC_EMBEDDINGS_FILENAME,
    SEMANTIC_INDEX_SCHEMA_VERSION,
    SEMANTIC_INDEX_SUBDIR,
    SEMANTIC_METADATA_FILENAME,
    SemanticIndexFreshnessSnapshot,
    SemanticIndexMetadata,
    SemanticIndexStatus,
    SemanticIndexStatusResult,
)
from engram.memory_retrieval.semantic_index_storage import (
    SemanticIndexStorage,
)
from engram.memory_retrieval.startup_orchestration import (
    StartupTaskMemoryRetrievalResult,
    orchestrate_startup_task_memory_retrieval,
)

__all__ = [
    "RetrievalQueryBuilderOptions",
    "RetrievalQueryMetadata",
    "TaskRetrievalQuery",
    "TaskMemoryCandidate",
    "TaskMemoryRetrievalMetadata",
    "TaskMemoryRetrievalOptions",
    "TaskMemoryRetrievalResult",
    "TaskMemoryPackOptions",
    "TaskMemoryPackedItem",
    "TaskMemoryPackMetadata",
    "TaskMemoryPackResult",
    "StartupTaskMemoryRetrievalResult",
    "SEMANTIC_BUILD_STATUS_SUCCESS",
    "SEMANTIC_EMBEDDINGS_FILENAME",
    "SEMANTIC_INDEX_SCHEMA_VERSION",
    "SEMANTIC_INDEX_SUBDIR",
    "SEMANTIC_METADATA_FILENAME",
    "SemanticIndexFreshnessSnapshot",
    "SemanticIndexMetadata",
    "SemanticIndexStatus",
    "SemanticIndexStatusResult",
    "SemanticIndexStorage",
    "resolve_task_memory_pack_options",
    "pack_task_memories",
    "normalize_fts_query_text",
    "build_task_retrieval_query",
    "retrieve_task_memory_candidates",
    "retrieve_task_memory_semantic_candidates",
    "orchestrate_startup_task_memory_retrieval",
]
