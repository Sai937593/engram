from engram.memory_retrieval.fts_query import EMPTY_FTS_QUERY


def _split_csv_tags(raw_tags: str | None) -> tuple[str, ...]:
    """Convert CSV tag storage to deterministic trimmed tuple order."""
    if not raw_tags:
        return ()
    return tuple(tag.strip() for tag in raw_tags.split(",") if tag.strip())


def _extract_terms_from_safe_query(safe_query: str) -> tuple[str, ...]:
    """Extract quoted terms from a normalized FTS query string."""
    if safe_query == EMPTY_FTS_QUERY:
        return ()
    return tuple(
        token[1:-1].casefold()
        for token in safe_query.split(" OR ")
        if len(token) >= 2 and token.startswith('"') and token.endswith('"')
    )
