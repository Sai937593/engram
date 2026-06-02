"""Phase lifecycle mutations with validation guards."""

from __future__ import annotations

from engram.models.phase import Phase
from engram.services.errors import JsonValue, ValidationError
from engram.services.serializers import phase_to_dict

PHASE_METADATA_FIELDS = {"title", "description", "acceptance", "evidence"}


def _normalize_phase_ref(value: str | None) -> str:
    """Normalize a phase reference for exact or legacy compatibility matching."""
    if value is None:
        return ""
    return " ".join(value.split()).casefold()


def _phase_matches_ref(phase: Phase, candidate: str) -> bool:
    """Return whether a phase matches a reference by ID, key, or legacy title."""
    normalized_candidate = _normalize_phase_ref(candidate)
    return (
        phase.id == candidate
        or phase.key == candidate
        or _normalize_phase_ref(phase.title) == normalized_candidate
    )


def resolve_phase_ref(project_id: str, phase_ref: str) -> Phase:
    candidate = phase_ref.strip()
    if not candidate:
        raise ValidationError(
            code="INVALID_PHASE_REFERENCE",
            message="Phase reference cannot be empty.",
            details={"phase_ref": phase_ref},
        )
    phase = Phase.get(candidate)
    if phase and phase.project_id == project_id:
        return phase
    matches = [
        project_phase
        for project_phase in Phase.list_by_project(project_id)
        if _phase_matches_ref(project_phase, candidate)
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValidationError(
            code="AMBIGUOUS_PHASE",
            message=f"Ambiguous phase '{candidate}'. Multiple phases match this title.",
            details={"phase_ref": candidate, "matches": [m.id for m in matches]},
        )
    raise ValidationError(
        code="PHASE_NOT_FOUND",
        message=f"Phase '{candidate}' not found in this project.",
        details={"project_id": project_id, "phase_ref": candidate},
    )


def _unfinished_phase_tasks(project_id: str, phase: Phase) -> list[str]:
    from engram.models.task import Task

    ids: list[str] = []
    normalized_title = _normalize_phase_ref(phase.title)
    normalized_key = _normalize_phase_ref(phase.key)
    for task in Task.list_by_project(project_id):
        in_phase = task.phase_id == phase.id
        if not in_phase and not task.phase_id:
            task_phase = _normalize_phase_ref(task.phase)
            in_phase = task_phase in {normalized_title, normalized_key}
        if in_phase and task.status not in ("done", "cancelled"):
            ids.append(task.id)
    return sorted(ids)


def _ensure_unique_phase_title(project_id: str, phase_id: str, title: str) -> None:
    normalized = " ".join(title.split()).casefold()
    for project_phase in Phase.list_by_project(project_id):
        if (
            project_phase.id != phase_id
            and " ".join(project_phase.title.split()).casefold() == normalized
        ):
            raise ValidationError(
                code="DUPLICATE_PHASE_TITLE",
                message=f"A phase with the title '{title}' already exists in this project.",
                details={"project_id": project_id, "title": title},
            )


def complete_phase(project_id: str, phase_ref: str) -> dict[str, JsonValue]:
    phase = resolve_phase_ref(project_id, phase_ref)
    unfinished = _unfinished_phase_tasks(project_id, phase)
    if unfinished:
        raise ValidationError(
            code="UNFINISHED_TASKS",
            message=f"Cannot complete phase '{phase.title}' because it has unfinished tasks.",
            details={"phase_id": phase.id, "unfinished_tasks": unfinished},
        )
    phase.update(status="done")
    return phase_to_dict(phase)


def update_phase(project_id: str, phase_ref: str, **updates: JsonValue) -> dict[str, JsonValue]:
    phase = resolve_phase_ref(project_id, phase_ref)
    pending_updates: dict[str, str] = {}
    for key, value in updates.items():
        if key not in PHASE_METADATA_FIELDS or value is None:
            continue
        if not isinstance(value, str):
            raise ValidationError(
                code="INVALID_PHASE_UPDATE",
                message=f"Phase field '{key}' must be a string.",
                details={"phase_id": phase.id, "field": key},
            )
        normalized = value.strip()
        if key == "title":
            if not normalized:
                raise ValidationError(
                    code="INVALID_PHASE_TITLE",
                    message="Phase title cannot be empty.",
                    details={"title": value},
                )
            _ensure_unique_phase_title(project_id, phase.id, normalized)
        pending_updates[key] = normalized
    if pending_updates:
        phase.update(**pending_updates)
    return phase_to_dict(phase)


def cancel_phase(
    project_id: str, phase_ref: str, reason: str | None = None
) -> dict[str, JsonValue]:
    phase = resolve_phase_ref(project_id, phase_ref)
    if phase.status in {"done", "cancelled"}:
        raise ValidationError(
            code="INVALID_PHASE_TRANSITION",
            message=f"Cannot transition phase '{phase.id}' from '{phase.status}' to 'cancelled'.",
            details={"phase_id": phase.id, "from_status": phase.status, "to_status": "cancelled"},
        )
    unfinished = _unfinished_phase_tasks(project_id, phase)
    if unfinished:
        raise ValidationError(
            code="UNFINISHED_TASKS",
            message=f"Cannot cancel phase '{phase.title}' because it has unfinished tasks.",
            details={"phase_id": phase.id, "unfinished_tasks": unfinished},
        )
    updates: dict[str, str] = {"status": "cancelled"}
    if reason and reason.strip():
        existing = phase.evidence or ""
        updates["evidence"] = (
            (existing + "\n" + reason.strip()).strip() if existing else reason.strip()
        )
    phase.update(**updates)
    return phase_to_dict(phase)


def archive_phase(project_id: str, phase_ref: str) -> dict[str, JsonValue]:
    phase = resolve_phase_ref(project_id, phase_ref)
    unfinished = _unfinished_phase_tasks(project_id, phase)
    if unfinished:
        raise ValidationError(
            code="UNFINISHED_TASKS",
            message=f"Cannot archive phase '{phase.title}' because it has unfinished tasks.",
            details={"phase_id": phase.id, "unfinished_tasks": unfinished},
        )
    if phase.status not in {"done", "cancelled"}:
        raise ValidationError(
            code="INVALID_PHASE_TRANSITION",
            message=f"Cannot transition phase '{phase.id}' from '{phase.status}' to 'deleted'.",
            details={"phase_id": phase.id, "from_status": phase.status, "to_status": "deleted"},
        )
    payload = phase_to_dict(phase)
    phase.delete()
    return {"archived": True, "phase": payload}
