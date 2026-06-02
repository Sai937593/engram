"""Phase query/create services and lifecycle re-exports."""

from __future__ import annotations

from engram.models.phase import Phase
from engram.services.errors import EngramServiceError, JsonValue, ValidationError
from engram.services.phase_completion_service import complete_phase
from engram.services.phase_lifecycle_service import (
    archive_phase,
    cancel_phase,
    resolve_phase_ref,
    update_phase,
)
from engram.services.serializers import phase_to_dict

VALID_PHASE_STATUSES = {
    "planned",
    "active",
    "review_pending",
    "done",
    "blocked",
    "cancelled",
    "all",
}
__all__ = [
    "archive_phase",
    "cancel_phase",
    "complete_phase",
    "create_phase",
    "get_active_phase",
    "list_phases",
    "resolve_phase_ref",
    "start_phase",
    "update_phase",
]


def _normalize_status(status: str | None) -> str:
    if status is None:
        return "all"
    normalized = status.strip().casefold()
    if normalized in VALID_PHASE_STATUSES:
        return normalized
    raise EngramServiceError(
        code="INVALID_PHASE_STATUS",
        message="Phase status filter is invalid.",
        details={"status": status, "allowed_statuses": sorted(VALID_PHASE_STATUSES)},
    )


def list_phases(project_id: str, status: str | None = None) -> list[dict[str, JsonValue]]:
    normalized_status = _normalize_status(status)
    phase_payloads = [phase_to_dict(phase_item) for phase_item in Phase.list_by_project(project_id)]
    if normalized_status == "all":
        return phase_payloads
    return [
        phase_payload
        for phase_payload in phase_payloads
        if phase_payload["status"] == normalized_status
    ]


def get_active_phase(project_id: str) -> dict[str, JsonValue] | None:
    phases = Phase.list_by_project(project_id)
    active_phase = next(
        (phase_item for phase_item in phases if phase_item.status == "active"), None
    )
    return None if active_phase is None else phase_to_dict(active_phase)


def start_phase(project_id: str, phase_ref: str) -> dict[str, JsonValue]:
    phase = resolve_phase_ref(project_id, phase_ref)
    refreshed, _ = Phase.start(phase.id)
    return phase_to_dict(refreshed)


def create_phase(
    project_id: str,
    title: str,
    description: str | None = None,
    status: str = "planned",
    acceptance: str | None = None,
    key: str | None = None,
) -> dict[str, JsonValue]:
    if not title or not title.strip():
        raise ValidationError(
            code="INVALID_PHASE_TITLE",
            message="Phase title cannot be empty.",
            details={"title": title},
        )
    if status not in Phase.VALID_STATUSES:
        raise ValidationError(
            code="INVALID_PHASE_STATUS",
            message=f"Phase status '{status}' is invalid.",
            details={"status": status, "allowed_statuses": sorted(Phase.VALID_STATUSES)},
        )
    normalized_candidate = " ".join(title.split()).casefold()
    for project_phase in Phase.list_by_project(project_id):
        if " ".join(project_phase.title.split()).casefold() == normalized_candidate:
            raise ValidationError(
                code="DUPLICATE_PHASE_TITLE",
                message=f"A phase with the title '{title}' already exists in this project.",
                details={"project_id": project_id, "title": title},
            )
        if key and key.strip() and getattr(project_phase, "key", None) == key.strip():
            raise ValidationError(
                code="DUPLICATE_PHASE_KEY",
                message=f"A phase with the key '{key.strip()}' already exists in this project.",
                details={"project_id": project_id, "key": key.strip()},
            )
    phase = Phase.create(
        project_id=project_id,
        title=title.strip(),
        description=description.strip() if description else None,
        status=status,
        acceptance=acceptance.strip() if acceptance else None,
        key=key.strip() if key and key.strip() else None,
    )
    return phase_to_dict(phase)
