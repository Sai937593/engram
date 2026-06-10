"""Focused contract and utility tests for retrieval support modules."""

import builtins

import pytest

from engram.memory_retrieval.fts_query import EMPTY_FTS_QUERY
from engram.memory_retrieval.fts_retriever.utils import (
    _extract_terms_from_safe_query,
    _split_csv_tags,
)
from engram.memory_retrieval.semantic_index_contract import (
    DEFAULT_SEMANTIC_MODEL_NAME,
    KNOWN_MODEL_DIMENSIONS,
    SemanticIndexMetadata,
    SemanticReindexError,
    load_semantic_embedding_dependencies,
    optional_str,
    resolve_semantic_model_dim,
)


def test_split_csv_tags_normalizes_empty_whitespace_and_order() -> None:
    assert _split_csv_tags(None) == ()
    assert _split_csv_tags("") == ()
    assert _split_csv_tags(" alpha, beta ,, gamma , ") == ("alpha", "beta", "gamma")


def test_extract_terms_from_safe_query_ignores_malformed_tokens() -> None:
    assert _extract_terms_from_safe_query(EMPTY_FTS_QUERY) == ()
    assert _extract_terms_from_safe_query('"Alpha" OR unquoted OR "Beta Term" OR "') == (
        "alpha",
        "beta term",
    )


def test_semantic_metadata_rejects_non_list_memory_ids(project) -> None:
    payload = SemanticIndexMetadata(
        schema_version=1,
        project_id=project.id,
        model_name=DEFAULT_SEMANTIC_MODEL_NAME,
        model_dim=KNOWN_MODEL_DIMENSIONS[DEFAULT_SEMANTIC_MODEL_NAME],
        indexed_memory_count=0,
        indexed_max_updated_at=None,
        build_started_at="2026-05-25T10:00:00Z",
        build_completed_at=None,
        build_status="success",
    ).to_dict()
    payload["memory_ids"] = "mem-1"

    with pytest.raises(ValueError, match="memory_ids"):
        SemanticIndexMetadata.from_dict(payload)


def test_optional_str_strips_blank_values() -> None:
    assert optional_str(None) is None
    assert optional_str("   ") is None
    assert optional_str("  value  ") == "value"
    assert optional_str(42) == "42"


def test_load_semantic_embedding_dependencies_reports_all_missing(monkeypatch) -> None:
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"numpy", "fastembed"}:
            raise ModuleNotFoundError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(SemanticReindexError) as raised:
        load_semantic_embedding_dependencies()

    message = str(raised.value)
    assert "fastembed" in message
    assert "numpy" in message
    assert "Install with" in message


def test_resolve_semantic_model_dim_uses_fallback_when_resolver_fails() -> None:
    class ExplodingEmbedding:
        @staticmethod
        def get_embedding_size(model_name: str) -> int:
            raise RuntimeError(f"cannot resolve {model_name}")

    assert (
        resolve_semantic_model_dim(
            model_name="custom-model",
            text_embedding_cls=ExplodingEmbedding,
            fallback_dim=768,
        )
        == 768
    )


def test_resolve_semantic_model_dim_uses_known_model_or_zero_fallback() -> None:
    class NoResolver:
        pass

    assert (
        resolve_semantic_model_dim(
            model_name=DEFAULT_SEMANTIC_MODEL_NAME,
            text_embedding_cls=NoResolver,
            fallback_dim=None,
        )
        == KNOWN_MODEL_DIMENSIONS[DEFAULT_SEMANTIC_MODEL_NAME]
    )
    assert (
        resolve_semantic_model_dim(
            model_name="unknown-model",
            text_embedding_cls=NoResolver,
            fallback_dim=None,
        )
        == 0
    )
