"""Phase service read operations."""

from __future__ import annotations

from engram.models.phase import Phase
from engram.services.errors import EngramServiceError, JsonValue
from engram.services.serializers import phase_to_dict

VALID_PHASE_STATUSES = {"planned", "active", "done", "blocked", "cancelled", "all"}


def _normalize_status(status: str | None) -> str:
    """Normalize and validate phase status filter values."""
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
    """Return project-scoped JSON-safe phase DTOs filtered by status."""
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
    """Return the active phase as a JSON-safe DTO, if one exists."""
    phases = Phase.list_by_project(project_id)
    active_phase = next(
        (phase_item for phase_item in phases if phase_item.status == "active"), None
    )
    if active_phase is None:
        return None
    return phase_to_dict(active_phase)
