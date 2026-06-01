"""Ready-promotion metadata quality evaluation helpers."""

from __future__ import annotations

EVALUATED_READY_FIELDS = ["description", "acceptance", "relevant_files"]


def evaluate_ready_metadata_quality(
    *,
    description: str | None,
    acceptance: str | None,
    relevant_files: list[str] | None,
) -> tuple[list[str], list[str], dict[str, str]]:
    """Return missing fields, weak fields, and weak-field reasons."""
    clean_description = (description or "").strip()
    clean_acceptance = (acceptance or "").strip()
    normalized_files = [item.strip() for item in (relevant_files or []) if item and item.strip()]

    missing_fields: list[str] = []
    weak_fields: list[str] = []
    weak_field_reasons: dict[str, str] = {}

    if not clean_description:
        missing_fields.append("description")
    if not clean_acceptance:
        missing_fields.append("acceptance")
    if not normalized_files:
        missing_fields.append("relevant_files")

    if clean_description and (len(clean_description) < 24 or len(clean_description.split()) < 4):
        weak_fields.append("description")
        weak_field_reasons["description"] = (
            "Description must include at least 4 words and 24 characters."
        )

    if clean_acceptance and (len(clean_acceptance) < 32 or len(clean_acceptance.split()) < 6):
        weak_fields.append("acceptance")
        weak_field_reasons["acceptance"] = (
            "Acceptance must include at least 6 words and 32 characters."
        )

    if normalized_files and not any(
        ("/" in item) or ("\\" in item) or ("." in item) for item in normalized_files
    ):
        weak_fields.append("relevant_files")
        weak_field_reasons["relevant_files"] = (
            "Relevant files must include at least one concrete path-like entry."
        )

    return missing_fields, weak_fields, weak_field_reasons
