"""Shared helpers for context generation."""


def compact_text(text: str | None) -> str:
    """Safely convert text to ASCII without truncation."""
    if not text:
        return ""
    return text.encode("ascii", errors="replace").decode("ascii")
