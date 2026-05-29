"""Shared helpers for context generation."""


def compact_text(text: str | None) -> str:
    """Safely convert text to ASCII without truncation, and strip whitespace."""
    if not text:
        return ""
    return text.strip().encode("ascii", errors="replace").decode("ascii")
