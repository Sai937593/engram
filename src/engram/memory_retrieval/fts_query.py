"""FTS-safe query normalization helpers for task-memory retrieval."""

from __future__ import annotations

import re

from engram.context.common import compact_text

EMPTY_FTS_QUERY = '""'
MAX_FTS_TERMS = 48
MAX_FTS_TERM_CHARS = 64
_TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)
_NON_SIGNAL_TERMS = frozenset(
    {
        "a",
        "an",
        "and",
        "context",
        "debug",
        "description",
        "for",
        "in",
        "not",
        "of",
        "or",
        "output",
        "phase",
        "query",
        "task",
        "tags",
        "test",
        "tests",
        "the",
        "title",
        "to",
        "with",
        "acceptance",
    }
)


def _extract_search_terms(
    query_text: str | None,
    *,
    max_terms: int = MAX_FTS_TERMS,
    max_term_chars: int = MAX_FTS_TERM_CHARS,
) -> list[str]:
    """Extract deterministic, de-duplicated terms from retrieval query text."""
    normalized = compact_text(query_text)
    if not normalized:
        return []

    terms: list[str] = []
    seen: set[str] = set()
    for token in _TOKEN_PATTERN.findall(normalized):
        cleaned = token.strip("_")
        if not cleaned:
            continue
        limited = cleaned[:max_term_chars]
        key = limited.casefold()
        if key in _NON_SIGNAL_TERMS:
            continue
        if key in seen:
            continue
        seen.add(key)
        terms.append(limited)
        if len(terms) >= max_terms:
            break
    return terms


def normalize_fts_query_text(
    query_text: str | None,
    *,
    max_terms: int = MAX_FTS_TERMS,
    max_term_chars: int = MAX_FTS_TERM_CHARS,
) -> str:
    """Convert arbitrary retrieval text to a syntactically safe SQLite FTS5 query."""
    terms = _extract_search_terms(
        query_text,
        max_terms=max_terms,
        max_term_chars=max_term_chars,
    )
    if not terms:
        return EMPTY_FTS_QUERY
    return " OR ".join(f'"{term}"' for term in terms)
