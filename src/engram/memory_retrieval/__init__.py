"""Memory retrieval helpers shared across startup and CLI flows."""

from engram.memory_retrieval.fts_query import normalize_fts_query_text
from engram.memory_retrieval.fts_retriever import (
    TaskMemoryCandidate,
    TaskMemoryRetrievalMetadata,
    TaskMemoryRetrievalOptions,
    TaskMemoryRetrievalResult,
    retrieve_task_memory_candidates,
)
from engram.memory_retrieval.query_builder import (
    RetrievalQueryBuilderOptions,
    RetrievalQueryMetadata,
    TaskRetrievalQuery,
    build_task_retrieval_query,
)

__all__ = [
    "RetrievalQueryBuilderOptions",
    "RetrievalQueryMetadata",
    "TaskRetrievalQuery",
    "TaskMemoryCandidate",
    "TaskMemoryRetrievalMetadata",
    "TaskMemoryRetrievalOptions",
    "TaskMemoryRetrievalResult",
    "normalize_fts_query_text",
    "build_task_retrieval_query",
    "retrieve_task_memory_candidates",
]
