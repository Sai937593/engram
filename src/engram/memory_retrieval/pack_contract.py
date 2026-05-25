"""Contracts for deterministic task-memory selection and budgeted packing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engram.memory_retrieval.retrieval_contract import (
        TaskMemoryCandidate,
        TaskMemoryRetrievalMetadata,
    )


DEFAULT_TASK_MEMORY_PACK_ORDERING = ("-boost_score", "fts_rank", "memory_id")


@dataclass(frozen=True)
class TaskMemoryPackOptions:
    """Deterministic limits used when packing retrieval candidates for startup."""

    section_char_budget: int = 3600
    preferred_k: int = 6
    max_k: int = 10
    max_item_chars: int = 420
    max_title_chars: int = 80
    max_tag_chars: int = 20
    max_tags_count: int = 5
    ordering_fields: tuple[str, ...] = DEFAULT_TASK_MEMORY_PACK_ORDERING
    dedupe_key: str = "memory_id"
    min_selection_boost_score: int = 1


@dataclass(frozen=True)
class TaskMemoryPackedItem:
    """One packed task-memory item selected from retrieval candidates."""

    memory_id: str
    type: str
    title: str
    content: str
    tags: tuple[str, ...]
    task_id: str | None
    retrieval_source: str
    fts_rank: float
    boost_score: int
    source_candidate_index: int
    char_count: int
    was_truncated: bool


@dataclass(frozen=True)
class TaskMemoryPackMetadata:
    """Pack-level metadata for deterministic debug output and test assertions."""

    project_id: str
    query_task_id: str
    source: str
    section_char_budget: int
    preferred_k: int
    max_k: int
    max_item_chars: int
    input_candidate_count: int
    unique_candidate_count: int
    selected_item_count: int
    hidden_item_count: int
    truncated_item_count: int
    used_char_count: int
    section_budget_exhausted: bool
    ordering_fields: tuple[str, ...]
    dedupe_key: str
    min_selection_boost_score: int = 1
    relevance_filtered_count: int = 0


@dataclass(frozen=True)
class TaskMemoryPackResult:
    """Packed items plus metadata for startup rendering and retrieval debug."""

    items: tuple[TaskMemoryPackedItem, ...]
    metadata: TaskMemoryPackMetadata


def resolve_task_memory_pack_options(
    options: TaskMemoryPackOptions | None,
) -> TaskMemoryPackOptions:
    """Return explicit pack options or deterministic defaults."""

    return options or TaskMemoryPackOptions()


def pack_task_memories(
    candidates: tuple[TaskMemoryCandidate, ...],
    retrieval_metadata: TaskMemoryRetrievalMetadata,
    options: TaskMemoryPackOptions | None = None,
) -> TaskMemoryPackResult:
    """Deterministic selection and budgeted packing of retrieved task memories."""
    opts = resolve_task_memory_pack_options(options)

    # 1. Index and sort candidates using stable sorting with fallback to original index
    import functools

    indexed_candidates = [(cand, idx) for idx, cand in enumerate(candidates)]

    def compare_items(
        item1: tuple[TaskMemoryCandidate, int],
        item2: tuple[TaskMemoryCandidate, int],
    ) -> int:
        cand1, idx1 = item1
        cand2, idx2 = item2
        for field in opts.ordering_fields:
            reverse = field.startswith("-")
            attr = field[1:] if reverse else field
            val1 = getattr(cand1, attr)
            val2 = getattr(cand2, attr)
            if val1 != val2:
                if reverse:
                    return 1 if val1 < val2 else -1
                else:
                    return 1 if val1 > val2 else -1
        # Fallback to stable input order (original index)
        return 1 if idx1 > idx2 else -1

    sorted_indexed_candidates = sorted(
        indexed_candidates,
        key=functools.cmp_to_key(compare_items),
    )

    # 2. Deduplicate candidates by dedupe_key (e.g. memory_id)
    seen_keys = set()
    unique_sorted_candidates: list[tuple[TaskMemoryCandidate, int]] = []
    for cand, idx in sorted_indexed_candidates:
        key_val = getattr(cand, opts.dedupe_key)
        if key_val not in seen_keys:
            seen_keys.add(key_val)
            unique_sorted_candidates.append((cand, idx))

    unique_candidate_count = len(unique_sorted_candidates)

    # 3. Budgeted packing loop
    selected_items: list[TaskMemoryPackedItem] = []
    used_char_count = 0
    section_budget_exhausted = False
    truncated_item_count = 0
    relevance_filtered_count = 0
    effective_k_limit = max(0, min(opts.preferred_k, opts.max_k))

    for cand, original_idx in unique_sorted_candidates:
        if cand.boost_score < opts.min_selection_boost_score:
            relevance_filtered_count += 1
            continue

        if len(selected_items) >= effective_k_limit:
            # Excluded by K limit, do not add
            continue

        # Title compaction
        title_truncated = len(cand.title or "") > opts.max_title_chars
        if title_truncated:
            if opts.max_title_chars <= 3:
                packed_title = (cand.title or "")[: opts.max_title_chars]
            else:
                packed_title = (cand.title or "")[: opts.max_title_chars - 3].rstrip() + "..."
        else:
            packed_title = cand.title or ""

        # Tags compaction
        tags_truncated = False
        packed_tags_list = []
        original_tags = cand.tags or ()
        if len(original_tags) > opts.max_tags_count:
            tags_truncated = True
            tags_to_process = original_tags[: opts.max_tags_count]
        else:
            tags_to_process = original_tags

        for tag in tags_to_process:
            if len(tag) > opts.max_tag_chars:
                tags_truncated = True
                if opts.max_tag_chars <= 3:
                    packed_tag = tag[: opts.max_tag_chars]
                else:
                    packed_tag = tag[: opts.max_tag_chars - 3].rstrip() + "..."
            else:
                packed_tag = tag
            packed_tags_list.append(packed_tag)
        packed_tags = tuple(packed_tags_list)

        # Content compaction
        content_truncated = len(cand.content or "") > opts.max_item_chars
        packed_content = (
            (cand.content or "")[: opts.max_item_chars]
            if content_truncated
            else (cand.content or "")
        )
        item_char_count = len(packed_content)

        item_was_truncated = title_truncated or tags_truncated or content_truncated

        if used_char_count + item_char_count > opts.section_char_budget:
            # Excluded by character budget limit
            section_budget_exhausted = True
            continue

        # We can select it!
        packed_item = TaskMemoryPackedItem(
            memory_id=cand.memory_id,
            type=cand.type,
            title=packed_title,
            content=packed_content,
            tags=packed_tags,
            task_id=cand.task_id,
            retrieval_source=cand.retrieval_source,
            fts_rank=cand.fts_rank,
            boost_score=cand.boost_score,
            source_candidate_index=original_idx,
            char_count=item_char_count,
            was_truncated=item_was_truncated,
        )
        selected_items.append(packed_item)
        used_char_count += item_char_count
        if item_was_truncated:
            truncated_item_count += 1

    # 4. Generate metadata and return result
    selected_item_count = len(selected_items)
    hidden_item_count = unique_candidate_count - selected_item_count

    pack_metadata = TaskMemoryPackMetadata(
        project_id=retrieval_metadata.project_id,
        query_task_id=retrieval_metadata.query_task_id,
        source=retrieval_metadata.source,
        section_char_budget=opts.section_char_budget,
        preferred_k=opts.preferred_k,
        max_k=opts.max_k,
        max_item_chars=opts.max_item_chars,
        input_candidate_count=len(candidates),
        unique_candidate_count=unique_candidate_count,
        selected_item_count=selected_item_count,
        hidden_item_count=hidden_item_count,
        truncated_item_count=truncated_item_count,
        used_char_count=used_char_count,
        section_budget_exhausted=section_budget_exhausted,
        ordering_fields=opts.ordering_fields,
        dedupe_key=opts.dedupe_key,
        min_selection_boost_score=opts.min_selection_boost_score,
        relevance_filtered_count=relevance_filtered_count,
    )

    return TaskMemoryPackResult(
        items=tuple(selected_items),
        metadata=pack_metadata,
    )
