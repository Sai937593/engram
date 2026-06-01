"""Executable metadata quality evaluation helpers."""

from __future__ import annotations

EVALUATED_READY_FIELDS = [
    "title",
    "description",
    "acceptance",
    "phase_id",
    "verification",
    "relevant_files",
    "search_hints",
]


def evaluate_executable_task_quality(
    *,
    title: str | None,
    description: str | None,
    acceptance: str | None,
    phase_id: str | None,
    verification: str | None,
    relevant_files: list[str] | None,
    search_hints: list[str] | None,
) -> tuple[list[str], list[str], dict[str, str]]:
    """Return missing fields, weak fields, and weak-field reasons for executable tasks."""
    clean_title = (title or "").strip()
    clean_description = (description or "").strip()
    clean_acceptance = (acceptance or "").strip()
    clean_phase_id = (phase_id or "").strip()
    clean_verification = (verification or "").strip()

    normalized_files = [item.strip() for item in (relevant_files or []) if item and item.strip()]
    normalized_hints = [item.strip() for item in (search_hints or []) if item and item.strip()]

    missing_fields: list[str] = []
    weak_fields: list[str] = []
    weak_field_reasons: dict[str, str] = {}

    # 1. Title
    if not clean_title:
        missing_fields.append("title")
    elif len(clean_title) < 10 or len(clean_title.split()) < 3:
        weak_fields.append("title")
        weak_field_reasons["title"] = "Title must include at least 3 words and 10 characters."

    # 2. Objective / Description
    if not clean_description:
        missing_fields.append("description")
    elif len(clean_description) < 24 or len(clean_description.split()) < 4:
        weak_fields.append("description")
        weak_field_reasons["description"] = (
            "Objective must include at least 4 words and 24 characters."
        )

    # 3. Acceptance
    if not clean_acceptance:
        missing_fields.append("acceptance")
    elif len(clean_acceptance) < 32 or len(clean_acceptance.split()) < 6:
        weak_fields.append("acceptance")
        weak_field_reasons["acceptance"] = (
            "Acceptance must include at least 6 words and 32 characters."
        )

    # 4. Phase ID
    if not clean_phase_id:
        missing_fields.append("phase_id")

    # 5. Verification
    if not clean_verification:
        missing_fields.append("verification")
    elif len(clean_verification) < 24 or len(clean_verification.split()) < 4:
        weak_fields.append("verification")
        weak_field_reasons["verification"] = (
            "Verification must include at least 4 words and 24 characters."
        )

    # 6. Relevant files or search hints choice
    if not normalized_files and not normalized_hints:
        missing_fields.append("relevant_files")
        missing_fields.append("search_hints")
    else:
        files_weak = False
        hints_weak = False
        files_weak_reason = ""
        hints_weak_reason = ""

        if normalized_files:
            if not any(
                ("/" in item) or ("\\" in item) or ("." in item) for item in normalized_files
            ):
                files_weak = True
                files_weak_reason = (
                    "Relevant files must include at least one concrete path-like entry."
                )

        if normalized_hints:
            if any(len(item) < 3 for item in normalized_hints):
                hints_weak = True
                hints_weak_reason = "Search hints must contain at least one valid search term."

        # Choice constraint: we only report weak if the choice overall is weak or both are weak
        if normalized_files and not normalized_hints:
            if files_weak:
                weak_fields.append("relevant_files")
                weak_field_reasons["relevant_files"] = files_weak_reason
        elif normalized_hints and not normalized_files:
            if hints_weak:
                weak_fields.append("search_hints")
                weak_field_reasons["search_hints"] = hints_weak_reason
        else:
            # Both are provided
            if files_weak and hints_weak:
                weak_fields.append("relevant_files")
                weak_fields.append("search_hints")
                weak_field_reasons["relevant_files"] = files_weak_reason
                weak_field_reasons["search_hints"] = hints_weak_reason

    return missing_fields, weak_fields, weak_field_reasons


def evaluate_ready_metadata_quality(
    *,
    description: str | None,
    acceptance: str | None,
    relevant_files: list[str] | None,
) -> tuple[list[str], list[str], dict[str, str]]:
    """Legacy compatibility helper."""
    missing, weak, reasons = evaluate_executable_task_quality(
        title="Placeholder title of the task",
        description=description,
        acceptance=acceptance,
        phase_id="placeholder-phase",
        verification="Placeholder verification command and expectation.",
        relevant_files=relevant_files,
        search_hints=None,
    )
    # Filter out placeholder fields from results
    missing = [m for m in missing if m not in ("title", "phase_id", "verification", "search_hints")]
    weak = [w for w in weak if w not in ("title", "phase_id", "verification", "search_hints")]
    reasons = {
        k: v
        for k, v in reasons.items()
        if k not in ("title", "phase_id", "verification", "search_hints")
    }
    return missing, weak, reasons
