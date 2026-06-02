"""Workflow status resolver for compact, machine-readable state lookup."""

from __future__ import annotations

from engram.models.phase import Phase
from engram.models.task import Task
from engram.services.errors import JsonValue
from engram.services.project_service import resolve_current_project
from engram.services.serializers import phase_to_dict, task_to_dict
from engram.services.workflow_helpers import task_matches_phase

PHASE_STATUS_ORDER = ("planned", "active", "review_pending", "done", "blocked", "cancelled")
TASK_STATUS_ORDER = ("open", "in_progress", "blocked", "done", "cancelled")
TASK_PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _select_phase(phases: list[Phase], status: str) -> Phase | None:
    return next((phase for phase in phases if phase.status == status), None)


def _select_active_task(project_id: str, active_phase: Phase | None) -> Task | None:
    tasks = Task.list_by_project(project_id)
    in_progress = [task for task in tasks if task.status in {"in_progress", "in-progress"}]
    candidates = (
        [task for task in in_progress if active_phase and task_matches_phase(task, active_phase)]
        if active_phase
        else []
    )
    if not candidates:
        candidates = in_progress
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda task: (TASK_PRIORITY_RANK.get(str(task.priority), 4), str(task.key or task.id)),
    )[0]


def _select_next_task(project_id: str, active_phase: Phase | None) -> Task | None:
    return Task.get_next(project_id, active_phase.id if active_phase else None)


def _count_phase_statuses(phases: list[Phase]) -> dict[str, int]:
    counts = {status: 0 for status in PHASE_STATUS_ORDER}
    for phase in phases:
        if phase.status in counts:
            counts[phase.status] += 1
    return counts


def _count_task_statuses(tasks: list[Task]) -> dict[str, int]:
    counts = {status: 0 for status in TASK_STATUS_ORDER}
    for task in tasks:
        status = str(task_to_dict(task)["effective_status"])
        if status in counts:
            counts[status] += 1
    return counts


def _slim_phase(phase: Phase) -> dict[str, JsonValue]:
    payload = phase_to_dict(phase)
    return {
        "id": payload["id"],
        "key": payload["key"],
        "title": payload["title"],
        "status": payload["status"],
    }


def _slim_task(task: Task) -> dict[str, JsonValue]:
    payload = task_to_dict(task)
    return {
        "id": payload["id"],
        "key": payload["key"],
        "title": payload["title"],
        "status": payload["effective_status"],
        "phase_id": payload["phase_id"],
        "phase_key": payload["phase_key"],
        "phase_title": payload["phase_title"],
        "is_verified": payload["is_verified"],
    }


def get_current_workflow_status(cwd: str | None = None) -> dict[str, JsonValue]:
    """Return the current workflow state in a compact deterministic payload."""
    project = resolve_current_project(cwd=cwd)
    project_id = str(project["id"])
    project_name = str(project["name"])
    plan_key = str(project.get("plan_key", project_id) or project_id)
    phases = Phase.list_by_project(project_id)
    tasks = Task.list_by_project(project_id)
    active_phase = _select_phase(phases, "active")
    review_phase = _select_phase(phases, "review_pending")
    active_task = _select_active_task(project_id, active_phase)
    next_task = _select_next_task(project_id, active_phase)
    active_task_payload = _slim_task(active_task) if active_task else None
    next_task_payload = _slim_task(next_task) if next_task else None

    if review_phase:
        review_phase_payload = _slim_phase(review_phase)
        next_action = {
            "tool": "engram_phase_complete",
            "reason": f"Phase {review_phase_payload['key']} is awaiting review completion.",
        }
    elif active_task_payload:
        if active_task_payload["is_verified"]:
            next_action = {
                "tool": "engram_workflow_finish_and_commit",
                "reason": f"Active task {active_task_payload['key']} is verified and ready to finish.",
            }
        else:
            next_action = {
                "tool": "engram_workflow_verify",
                "reason": f"Active task {active_task_payload['key']} is in progress and needs verification.",
            }
    elif next_task_payload:
        next_action = {
            "tool": "engram_workflow_start",
            "reason": f"Start the next actionable task {next_task_payload['key']}.",
        }
    else:
        next_action = {
            "tool": "engram_task_create",
            "reason": "No actionable tasks exist. Create the next task.",
        }

    payload: dict[str, JsonValue] = {
        "project": {"id": project_id, "name": project_name},
        "plan": {"key": plan_key},
        "counts": {"phases": _count_phase_statuses(phases), "tasks": _count_task_statuses(tasks)},
        "next_action": next_action,
    }
    if active_phase:
        payload["active_phase"] = _slim_phase(active_phase)
    if review_phase:
        payload["review_phase"] = _slim_phase(review_phase)
    if active_task_payload:
        payload["active_task"] = active_task_payload
    if next_task_payload:
        payload["next_task"] = next_task_payload
    return payload
