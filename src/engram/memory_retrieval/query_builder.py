"""Task retrieval query builder independent of retrieval backends."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from engram.context_helpers.common import compact_text
from engram.models.phase import Phase
from engram.models.task import Task

ELLIPSIS = "..."


@dataclass(frozen=True)
class RetrievalQueryBuilderOptions:
    """Deterministic limits for retrieval query construction."""

    max_query_chars: int = 1200
    field_char_limit: int = 220
    include_phase_fields: bool = True
    include_context_fields: bool = True


@dataclass(frozen=True)
class RetrievalQueryMetadata:
    """Structured debug metadata emitted by the retrieval query builder."""

    task_id: str
    project_id: str
    phase_id: str | None
    phase_title: str | None
    included_fields: tuple[str, ...]
    omitted_fields: tuple[str, ...]
    truncated_fields: tuple[str, ...]
    query_char_count: int
    query_was_capped: bool


@dataclass(frozen=True)
class TaskRetrievalQuery:
    """Query payload reused by retrieval callers and debug output."""

    query_text: str
    fragments: tuple[str, ...]
    metadata: RetrievalQueryMetadata


def _normalize_text(text: str | None) -> str:
    """Normalize text to compact ASCII-safe single-line content."""
    compacted = compact_text(text)
    return " ".join(compacted.split())


def _truncate_with_limit(text: str, limit: int) -> tuple[str, bool]:
    """Apply deterministic truncation and return whether truncation occurred."""
    if not text or limit <= 0:
        return "", bool(text)
    if len(text) <= limit:
        return text, False
    if limit <= len(ELLIPSIS):
        return text[:limit], True
    return f"{text[: limit - len(ELLIPSIS)].rstrip()}{ELLIPSIS}", True


def _format_fragment(field_name: str, value: str) -> str:
    """Render one field fragment in stable key-value form."""
    return f"{field_name}: {value}"


def _sorted_tags(tags: list[str] | tuple[str, ...] | None) -> str:
    """Return deterministic comma-separated tags."""
    if not tags:
        return ""
    cleaned = {_normalize_text(tag) for tag in tags if _normalize_text(tag)}
    return ", ".join(sorted(cleaned, key=str.casefold))


def _build_context_fields(context: Mapping[str, str | None] | None) -> list[tuple[str, str]]:
    """Return normalized context fields sorted for deterministic output."""
    if not context:
        return []

    fields: list[tuple[str, str]] = []
    for key in sorted(context.keys(), key=str.casefold):
        normalized_key = _normalize_text(key)
        normalized_value = _normalize_text(context.get(key))
        if normalized_key and normalized_value:
            fields.append((f"context.{normalized_key}", normalized_value))
    return fields


def _resolve_phase_context(
    selected_task: Task,
    active_phase: Phase | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Resolve phase context from active phase, phase_id link, then legacy phase title."""
    if active_phase:
        return (
            active_phase.id,
            _normalize_text(active_phase.title),
            _normalize_text(active_phase.description),
            _normalize_text(active_phase.acceptance),
        )

    if selected_task.phase_id:
        resolved_phase = Phase.get(selected_task.phase_id)
        if resolved_phase:
            return (
                resolved_phase.id,
                _normalize_text(resolved_phase.title),
                _normalize_text(resolved_phase.description),
                _normalize_text(resolved_phase.acceptance),
            )

    legacy_phase_title = _normalize_text(selected_task.phase)
    return (
        selected_task.phase_id,
        legacy_phase_title or None,
        None,
        None,
    )


def build_task_retrieval_query(
    selected_task: Task,
    active_phase: Phase | None = None,
    context: Mapping[str, str | None] | None = None,
    options: RetrievalQueryBuilderOptions | None = None,
) -> TaskRetrievalQuery:
    """Build deterministic retrieval query text from task, phase, and optional context."""
    resolved_options = options or RetrievalQueryBuilderOptions()
    (
        resolved_phase_id,
        resolved_phase_title,
        resolved_phase_description,
        resolved_phase_acceptance,
    ) = _resolve_phase_context(selected_task, active_phase)

    raw_fields: list[tuple[str, str | None]] = [
        ("task.title", selected_task.title),
        ("task.description", selected_task.description),
        ("task.acceptance", selected_task.acceptance),
        ("task.tags", _sorted_tags(selected_task.tags)),
    ]

    if resolved_options.include_phase_fields and (
        resolved_phase_title or resolved_phase_description or resolved_phase_acceptance
    ):
        raw_fields.extend(
            [
                ("phase.title", resolved_phase_title),
                ("phase.description", resolved_phase_description),
                ("phase.acceptance", resolved_phase_acceptance),
            ]
        )

    if resolved_options.include_context_fields:
        raw_fields.extend(_build_context_fields(context))

    omitted_fields = ["task.evidence"]
    if resolved_phase_title or resolved_phase_description or resolved_phase_acceptance:
        omitted_fields.append("phase.evidence")

    included_fields: list[str] = []
    truncated_fields: list[str] = []
    fragments: list[str] = []

    for field_name, raw_value in raw_fields:
        normalized_value = _normalize_text(raw_value)
        if not normalized_value:
            omitted_fields.append(field_name)
            continue

        limited_value, truncated = _truncate_with_limit(
            normalized_value,
            resolved_options.field_char_limit,
        )
        fragments.append(_format_fragment(field_name, limited_value))
        included_fields.append(field_name)
        if truncated:
            truncated_fields.append(field_name)

    query_text = " | ".join(fragments)
    capped_query_text, query_was_capped = _truncate_with_limit(
        query_text,
        resolved_options.max_query_chars,
    )

    metadata = RetrievalQueryMetadata(
        task_id=selected_task.id,
        project_id=selected_task.project_id,
        phase_id=resolved_phase_id,
        phase_title=resolved_phase_title,
        included_fields=tuple(included_fields),
        omitted_fields=tuple(omitted_fields),
        truncated_fields=tuple(truncated_fields),
        query_char_count=len(capped_query_text),
        query_was_capped=query_was_capped,
    )
    return TaskRetrievalQuery(
        query_text=capped_query_text,
        fragments=tuple(fragments),
        metadata=metadata,
    )
