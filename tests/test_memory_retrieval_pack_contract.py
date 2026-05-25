"""Tests for task-memory packing contracts."""

from dataclasses import asdict

from engram.memory_retrieval.pack_contract import (
    DEFAULT_TASK_MEMORY_PACK_ORDERING,
    TaskMemoryPackedItem,
    TaskMemoryPackMetadata,
    TaskMemoryPackOptions,
    TaskMemoryPackResult,
    pack_task_memories,
    resolve_task_memory_pack_options,
)
from engram.memory_retrieval.retrieval_contract import (
    TaskMemoryCandidate,
    TaskMemoryRetrievalMetadata,
)


def test_pack_options_defaults_cover_phase_six_budget_controls() -> None:
    options = TaskMemoryPackOptions()

    assert options.section_char_budget == 3600
    assert options.preferred_k == 6
    assert options.max_k == 10
    assert options.max_item_chars == 420
    assert options.ordering_fields == DEFAULT_TASK_MEMORY_PACK_ORDERING
    assert options.dedupe_key == "memory_id"
    assert options.min_selection_boost_score == 1


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


def _mock_candidate(
    memory_id: str,
    content: str = "some content",
    boost_score: int = 1,
    fts_rank: float = 1.0,
    task_id: str | None = None,
) -> TaskMemoryCandidate:
    return TaskMemoryCandidate(
        memory_id=memory_id,
        project_id="proj-01",
        scope="task",
        type="lesson",
        task_id=task_id,
        title=f"Title for {memory_id}",
        content=content,
        tags=("tag1",),
        retrieval_source="fts",
        fts_rank=fts_rank,
        boost_score=boost_score,
        task_id_match=False,
        title_term_hits=(),
        tag_term_hits=(),
    )


def _mock_retrieval_metadata(
    project_id: str = "proj-01",
    query_task_id: str = "task-01",
    source: str = "fts",
) -> TaskMemoryRetrievalMetadata:
    return TaskMemoryRetrievalMetadata(
        project_id=project_id,
        query_task_id=query_task_id,
        source=source,
        requested_query_text="query",
        normalized_fts_query="query",
        query_term_count=1,
        query_was_empty=False,
        fallback_used=False,
        fallback_reason=None,
        max_candidates=20,
        scanned_row_count=10,
        returned_candidate_count=10,
    )


def test_pack_task_memories_deduplicates_by_memory_id() -> None:
    cand1 = _mock_candidate("mem-1", content="first", boost_score=5, fts_rank=0.1)
    cand2 = _mock_candidate("mem-1", content="second", boost_score=2, fts_rank=0.5)

    candidates = (cand1, cand2)
    ret_meta = _mock_retrieval_metadata()

    result = pack_task_memories(candidates, ret_meta)

    # Should collapse to 1 item
    assert len(result.items) == 1
    # The higher rank one (first, since boost_score=5 > 2) is chosen due to sorting
    assert result.items[0].memory_id == "mem-1"
    assert result.items[0].content == "first"
    assert result.items[0].boost_score == 5

    assert result.metadata.input_candidate_count == 2
    assert result.metadata.unique_candidate_count == 1
    assert result.metadata.selected_item_count == 1
    assert result.metadata.hidden_item_count == 0


def test_pack_task_memories_stable_sorting_and_tie_breaking() -> None:
    # Ties on boost_score and fts_rank, memory_id is different
    cand1 = _mock_candidate("mem-b", boost_score=5, fts_rank=0.2)
    cand2 = _mock_candidate("mem-a", boost_score=5, fts_rank=0.2)

    result = pack_task_memories((cand1, cand2), _mock_retrieval_metadata())
    # "mem-a" should be first because of alphabetical memory_id order asc
    assert result.items[0].memory_id == "mem-a"
    assert result.items[1].memory_id == "mem-b"

    # Now test custom ordering fields: e.g. sorting by memory_id descending
    options = TaskMemoryPackOptions(ordering_fields=("-memory_id",))
    result_desc = pack_task_memories((cand2, cand1), _mock_retrieval_metadata(), options)
    assert result_desc.items[0].memory_id == "mem-b"
    assert result_desc.items[1].memory_id == "mem-a"

    # Test tie breaker fallback to original index when all ordering fields are equal
    # Let's use ordering_fields without memory_id, so only boost_score
    cand_first = _mock_candidate("mem-x", boost_score=5)
    cand_second = _mock_candidate("mem-y", boost_score=5)
    options_boost = TaskMemoryPackOptions(ordering_fields=("boost_score",))
    result_tie = pack_task_memories(
        (cand_first, cand_second), _mock_retrieval_metadata(), options_boost
    )
    # Should preserve original stable index (cand_first, then cand_second)
    assert result_tie.items[0].memory_id == "mem-x"
    assert result_tie.items[1].memory_id == "mem-y"


def test_pack_task_memories_enforces_max_k_limit() -> None:
    candidates = tuple(_mock_candidate(f"mem-{i}", boost_score=10 - i) for i in range(15))
    options = TaskMemoryPackOptions(max_k=5)

    result = pack_task_memories(candidates, _mock_retrieval_metadata(), options)

    assert len(result.items) == 5
    assert result.metadata.selected_item_count == 5
    assert result.metadata.unique_candidate_count == 15
    assert result.metadata.hidden_item_count == 10
    # Sorted order means mem-0 to mem-4 are selected (highest boost scores)
    assert [item.memory_id for item in result.items] == [f"mem-{i}" for i in range(5)]


def test_pack_task_memories_enforces_preferred_k_before_max_k() -> None:
    candidates = tuple(_mock_candidate(f"mem-{i}", boost_score=20 - i) for i in range(8))
    options = TaskMemoryPackOptions(preferred_k=3, max_k=6)

    result = pack_task_memories(candidates, _mock_retrieval_metadata(), options)

    assert len(result.items) == 3
    assert result.metadata.selected_item_count == 3
    assert result.metadata.unique_candidate_count == 8
    assert result.metadata.hidden_item_count == 5
    assert [item.memory_id for item in result.items] == ["mem-0", "mem-1", "mem-2"]


def test_pack_task_memories_can_return_fewer_than_preferred_k_for_weak_candidates() -> None:
    candidates = (
        _mock_candidate("mem-weak-1", boost_score=0, content="weak-one"),
        _mock_candidate("mem-weak-2", boost_score=0, content="weak-two"),
        _mock_candidate("mem-strong-1", boost_score=3, content="strong"),
    )
    options = TaskMemoryPackOptions(preferred_k=6, max_k=10, min_selection_boost_score=1)

    result = pack_task_memories(candidates, _mock_retrieval_metadata(), options)

    assert [item.memory_id for item in result.items] == ["mem-strong-1"]
    assert result.metadata.selected_item_count == 1
    assert result.metadata.hidden_item_count == 2
    assert result.metadata.relevance_filtered_count == 2


def test_pack_task_memories_weak_only_candidates_yield_concise_empty_pack() -> None:
    candidates = (
        _mock_candidate("mem-weak-1", boost_score=0, content="weak-one"),
        _mock_candidate("mem-weak-2", boost_score=0, content="weak-two"),
    )
    options = TaskMemoryPackOptions(min_selection_boost_score=1)

    result = pack_task_memories(candidates, _mock_retrieval_metadata(), options)

    assert result.items == ()
    assert result.metadata.selected_item_count == 0
    assert result.metadata.hidden_item_count == 2
    assert result.metadata.relevance_filtered_count == 2
    assert result.metadata.section_budget_exhausted is False


def test_pack_task_memories_enforces_section_char_budget() -> None:
    cand1 = _mock_candidate("mem-1", content="hello", boost_score=10)  # 5 chars
    cand2 = _mock_candidate("mem-2", content="world!", boost_score=9)  # 6 chars
    cand3 = _mock_candidate("mem-3", content="excluded", boost_score=8)  # 8 chars

    # Set budget to 11 chars. mem-1 (5) and mem-2 (6) will fit (11 chars).
    # mem-3 (8 chars) will exceed the 11 budget.
    options = TaskMemoryPackOptions(section_char_budget=11)

    result = pack_task_memories((cand1, cand2, cand3), _mock_retrieval_metadata(), options)

    assert len(result.items) == 2
    assert [item.memory_id for item in result.items] == ["mem-1", "mem-2"]
    assert result.metadata.used_char_count == 11
    assert result.metadata.section_budget_exhausted is True
    assert result.metadata.hidden_item_count == 1


def test_pack_task_memories_truncates_long_contents() -> None:
    long_content = "a" * 100
    cand = _mock_candidate("mem-1", content=long_content)

    options = TaskMemoryPackOptions(max_item_chars=10)
    result = pack_task_memories((cand,), _mock_retrieval_metadata(), options)

    assert len(result.items) == 1
    assert result.items[0].content == "a" * 10
    assert result.items[0].was_truncated is True
    assert result.items[0].char_count == 10
    assert result.metadata.truncated_item_count == 1


def test_pack_task_memories_truncates_long_titles() -> None:
    # A candidate with a title of 20 characters
    cand = TaskMemoryCandidate(
        memory_id="mem-1",
        project_id="proj-01",
        scope="task",
        type="lesson",
        task_id=None,
        title="VeryLongMemoryTitleHere",  # 23 characters
        content="short content",
        tags=("tag1",),
        retrieval_source="fts",
        fts_rank=1.0,
        boost_score=1,
        task_id_match=False,
        title_term_hits=(),
        tag_term_hits=(),
    )

    # Limit title to 10 characters.
    # Compacted title should be "VeryLon..." (length 10)
    options = TaskMemoryPackOptions(max_title_chars=10)
    result = pack_task_memories((cand,), _mock_retrieval_metadata(), options)

    assert len(result.items) == 1
    assert result.items[0].title == "VeryLon..."
    assert result.items[0].was_truncated is True
    assert result.metadata.truncated_item_count == 1


def test_pack_task_memories_truncates_long_tags() -> None:
    cand = TaskMemoryCandidate(
        memory_id="mem-1",
        project_id="proj-01",
        scope="task",
        type="lesson",
        task_id=None,
        title="Title",
        content="short content",
        tags=("extremelylongtagname", "tag2", "tag3"),
        retrieval_source="fts",
        fts_rank=1.0,
        boost_score=1,
        task_id_match=False,
        title_term_hits=(),
        tag_term_hits=(),
    )

    # Limit to max_tags_count = 2 and max_tag_chars = 8
    # "extremelylongtagname" should be compacted to "extre..." (length 8)
    # The tag list should be capped to 2 tags: ("extre...", "tag2")
    options = TaskMemoryPackOptions(max_tags_count=2, max_tag_chars=8)
    result = pack_task_memories((cand,), _mock_retrieval_metadata(), options)

    assert len(result.items) == 1
    assert result.items[0].tags == ("extre...", "tag2")
    assert result.items[0].was_truncated is True
    assert result.metadata.truncated_item_count == 1


def test_pack_task_memories_short_limits_edge_cases() -> None:
    cand = TaskMemoryCandidate(
        memory_id="mem-1",
        project_id="proj-01",
        scope="task",
        type="lesson",
        task_id=None,
        title="LongTitle",
        content="short content",
        tags=("longtag",),
        retrieval_source="fts",
        fts_rank=1.0,
        boost_score=1,
        task_id_match=False,
        title_term_hits=(),
        tag_term_hits=(),
    )

    # Set very small limits where limits <= 3
    # Title truncated to exactly 3 chars, Tag truncated to exactly 2 chars
    options = TaskMemoryPackOptions(max_title_chars=3, max_tag_chars=2)
    result = pack_task_memories((cand,), _mock_retrieval_metadata(), options)

    assert len(result.items) == 1
    assert result.items[0].title == "Lon"
    assert result.items[0].tags == ("lo",)
    assert result.items[0].was_truncated is True
    assert result.metadata.truncated_item_count == 1
