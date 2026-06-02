"""Phase completion lifecycle checks."""

from __future__ import annotations

from engram.models.phase import Phase
from engram.models.task import Task
from engram.services.errors import JsonValue, ValidationError
from engram.services.phase_lifecycle_service import _normalize_phase_ref, resolve_phase_ref
from engram.services.serializers import phase_to_dict


def _unfinished_phase_tasks(project_id: str, phase: Phase) -> list[str]:
    ids: list[str] = []
    normalized_title = _normalize_phase_ref(phase.title)
    normalized_key = _normalize_phase_ref(phase.key)
    for task in Task.list_by_project(project_id):
        in_phase = task.phase_id == phase.id
        if not in_phase and not task.phase_id:
            in_phase = _normalize_phase_ref(task.phase) in {normalized_title, normalized_key}
        if in_phase and task.status not in ("done", "cancelled"):
            ids.append(task.id)
    return sorted(ids)


def complete_phase(project_id: str, phase_ref: str) -> dict[str, JsonValue]:
    phase = resolve_phase_ref(project_id, phase_ref)
    unfinished = _unfinished_phase_tasks(project_id, phase)
    if phase.status != "review_pending":
        details: dict[str, JsonValue] = {
            "phase_id": phase.id,
            "phase_status": phase.status,
            "required_status": "review_pending",
        }
        if unfinished:
            details["unfinished_tasks"] = unfinished
        raise ValidationError(
            code="PHASE_COMPLETION_BLOCKED",
            message=(
                f"Cannot complete phase '{phase.title}' because it is '{phase.status}', not "
                "'review_pending'."
            ),
            details=details,
            fix=(
                "Finish any unfinished tasks, let the phase reach review_pending, then retry "
                "engram_phase_complete."
                if unfinished
                else "Move the phase to review_pending before retrying engram_phase_complete."
            ),
        )
    if unfinished:
        raise ValidationError(
            code="UNFINISHED_TASKS",
            message=(
                f"Cannot complete phase '{phase.title}' because it still has unfinished tasks: "
                f"{', '.join(unfinished)}."
            ),
            details={"phase_id": phase.id, "unfinished_tasks": unfinished},
            fix="Finish or cancel the listed tasks, then retry engram_phase_complete.",
        )
    phase.update(status="done")
    return phase_to_dict(phase)
