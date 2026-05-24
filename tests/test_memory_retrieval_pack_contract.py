"""Tests for task-memory packing contracts."""

from dataclasses import asdict

from engram.memory_retrieval.pack_contract import (
    DEFAULT_TASK_MEMORY_PACK_ORDERING,
    TaskMemoryPackedItem,
    TaskMemoryPackMetadata,
    TaskMemoryPackOptions,
    TaskMemoryPackResult,
    resolve_task_memory_pack_options,
)


def test_pack_options_defaults_cover_phase_six_budget_controls() -> None:
    options = TaskMemoryPackOptions()

    assert options.section_char_budget == 3600
    assert options.preferred_k == 6
    assert options.max_k == 10
    assert options.max_item_chars == 420
    assert options.ordering_fields == DEFAULT_TASK_MEMORY_PACK_ORDERING
    assert options.dedupe_key == "memory_id"


def test_resolve_pack_options_returns_explicit_or_default_options() -> None:
    explicit = TaskMemoryPackOptions(section_char_budget=2400, preferred_k=5, max_k=8)

    assert resolve_task_memory_pack_options(explicit) == explicit
    assert resolve_task_memory_pack_options(None) == TaskMemoryPackOptions()


def test_pack_metadata_and_result_shape_are_stable() -> None:
    packed_item = TaskMemoryPackedItem(
        memory_id="mem-01",
        type="lesson",
        title="Keep retrieval deterministic",
        content="Sort by boost, then rank, then memory id.",
        tags=("retrieval", "phase-6"),
        task_id="task-01",
        retrieval_source="fts",
        fts_rank=1.0,
        boost_score=4,
        source_candidate_index=0,
        char_count=65,
        was_truncated=True,
    )
    metadata = TaskMemoryPackMetadata(
        project_id="proj-01",
        query_task_id="task-01",
        source="fts",
        section_char_budget=3200,
        preferred_k=6,
        max_k=10,
        max_item_chars=420,
        input_candidate_count=9,
        unique_candidate_count=8,
        selected_item_count=6,
        hidden_item_count=2,
        truncated_item_count=1,
        used_char_count=1800,
        section_budget_exhausted=False,
        ordering_fields=("-boost_score", "fts_rank", "memory_id"),
        dedupe_key="memory_id",
    )
    result = TaskMemoryPackResult(items=(packed_item,), metadata=metadata)
    metadata_dict = asdict(metadata)

    assert list(metadata_dict.keys()) == list(TaskMemoryPackMetadata.__dataclass_fields__.keys())
    assert metadata.hidden_item_count == 2
    assert metadata.truncated_item_count == 1
    assert metadata.ordering_fields == ("-boost_score", "fts_rank", "memory_id")
    assert result.items[0].was_truncated is True
    assert result.metadata.max_k == 10
