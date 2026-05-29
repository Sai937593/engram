"""Phase service read operations."""

from __future__ import annotations

from engram.models.phase import Phase
from engram.services.errors import EngramServiceError, JsonValue, ValidationError
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


def resolve_phase_ref(project_id: str, phase_ref: str) -> Phase:
    """Resolve a phase reference (ID or title) to a Phase model instance within the project."""
    candidate = phase_ref.strip()
    if not candidate:
        raise ValidationError(
            code="INVALID_PHASE_REFERENCE",
            message="Phase reference cannot be empty.",
            details={"phase_ref": phase_ref},
        )

    # Try ID lookup first
    phase = Phase.get(candidate)
    if phase and phase.project_id == project_id:
        return phase

    # Try title matching
    normalized_candidate = " ".join(candidate.split()).casefold()
    matching_phases = [
        project_phase
        for project_phase in Phase.list_by_project(project_id)
        if " ".join(project_phase.title.split()).casefold() == normalized_candidate
    ]

    if len(matching_phases) == 1:
        return matching_phases[0]
    elif len(matching_phases) > 1:
        matches = ", ".join(f"{match.id} ({match.title})" for match in matching_phases)
        raise ValidationError(
            code="AMBIGUOUS_PHASE",
            message=f"Ambiguous phase '{candidate}'. Multiple phases match this title: {matches}",
            details={
                "phase_ref": candidate,
                "matches": [m.id for m in matching_phases],
            },
        )
    else:
        raise ValidationError(
            code="PHASE_NOT_FOUND",
            message=f"Phase '{candidate}' not found in this project.",
            details={"project_id": project_id, "phase_ref": candidate},
        )


def start_phase(project_id: str, phase_ref: str) -> dict[str, JsonValue]:
    """Start a phase and return its updated JSON-safe DTO, demoting other active phases."""
    phase = resolve_phase_ref(project_id, phase_ref)
    refreshed, _ = Phase.start(phase.id)
    return phase_to_dict(refreshed)


def complete_phase(project_id: str, phase_ref: str) -> dict[str, JsonValue]:
    """Complete a phase, validating that it has no unfinished tasks."""
    phase = resolve_phase_ref(project_id, phase_ref)

    from engram.models.task import Task

    tasks = Task.list_by_project(project_id)
    unfinished = []
    normalized_phase_title = " ".join(phase.title.split()).casefold()

    for t in tasks:
        in_phase = False
        if t.phase_id == phase.id:
            in_phase = True
        elif (
            not t.phase_id
            and " ".join((t.phase or "").split()).casefold() == normalized_phase_title
        ):
            in_phase = True

        if in_phase and t.status not in ("done", "cancelled"):
            unfinished.append(t)

    if unfinished:
        raise ValidationError(
            code="UNFINISHED_TASKS",
            message=f"Cannot complete phase '{phase.title}' because it has unfinished tasks.",
            details={
                "phase_id": phase.id,
                "unfinished_tasks": sorted([t.id for t in unfinished]),
            },
        )

    phase.update(status="done")
    return phase_to_dict(phase)


def create_phase(
    project_id: str,
    title: str,
    description: str | None = None,
    status: str = "planned",
    acceptance: str | None = None,
) -> dict[str, JsonValue]:
    """Create a new phase in the project and return its JSON-safe DTO."""
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
            details={"status": status, "allowed_statuses": sorted(list(Phase.VALID_STATUSES))},
        )

    normalized_candidate = " ".join(title.split()).casefold()
    matching_phases = [
        project_phase
        for project_phase in Phase.list_by_project(project_id)
        if " ".join(project_phase.title.split()).casefold() == normalized_candidate
    ]
    if matching_phases:
        raise ValidationError(
            code="DUPLICATE_PHASE_TITLE",
            message=f"A phase with the title '{title}' already exists in this project.",
            details={"project_id": project_id, "title": title},
        )

    phase = Phase.create(
        project_id=project_id,
        title=title.strip(),
        description=description.strip() if description else None,
        status=status,
        acceptance=acceptance.strip() if acceptance else None,
    )
    return phase_to_dict(phase)
