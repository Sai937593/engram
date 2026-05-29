"""Common helper functions for MCP tools."""

from __future__ import annotations

from typing import Any

import yaml

from engram.services.errors import EngramServiceError


def _respond(data: dict[str, Any], keep_empty_keys: set[str] | None = None) -> str:
    """Recursively strip None values and empty lists/dicts, then serialize to YAML."""
    keys_to_keep = keep_empty_keys or set()

    def prune(val: Any, key: str | None = None) -> Any:
        if isinstance(val, dict):
            pruned_dict = {}
            for k, v in val.items():
                pruned_v = prune(v, k)
                if (
                    pruned_v is not None
                    and (pruned_v != [] or k in keys_to_keep)
                    and (pruned_v != {} or k in keys_to_keep)
                ):
                    pruned_dict[k] = pruned_v
            return pruned_dict
        elif isinstance(val, list):
            pruned_list = []
            for item in val:
                pruned_item = prune(item, None)
                if pruned_item is not None and pruned_item != [] and pruned_item != {}:
                    pruned_list.append(pruned_item)
            return pruned_list
        return val

    pruned_data = prune(data)
    return yaml.safe_dump(pruned_data, sort_keys=False)


def _respond_error(exc: EngramServiceError) -> str:
    """Format an EngramServiceError into a flat YAML error response."""
    known_fixes = {
        "DEPENDENCY_UNSATISFIED": "Complete all prerequisite tasks using engram_task_done before starting this task.",
        "NO_TASK_IN_PROGRESS": "Start a task first using engram_task_start.",
        "TASK_NOT_FOUND": "List tasks using engram_task_list to find the correct task ID or reference.",
        "TASK_AMBIGUOUS": "Use the exact 8-character task ID instead of the title. Run engram_task_list to find the task ID.",
        "DIRTY_WORKING_TREE": "Commit your changes using engram_workflow_finish or stash them before starting a new task.",
        "INVALID_TASK_STATUS": "Use a valid task status (todo, in-progress, done, blocked, or cancelled) and update using engram_task_update.",
        "PHASE_COMPLETION_BLOCKED": "Complete all unfinished tasks in the phase using engram_task_done, or update/cancel them using engram_task_update before completing the phase.",
        "UNFINISHED_TASKS": "Complete all unfinished tasks in the phase using engram_task_done, or update/cancel them using engram_task_update before completing the phase.",
    }

    fix_val = getattr(exc, "fix", None) or known_fixes.get(exc.code)

    resp_dict: dict[str, Any] = {
        "ok": False,
        "error": exc.code,
        "message": exc.message,
    }
    if fix_val:
        resp_dict["fix"] = fix_val

    return _respond(resp_dict)


def slim_task_dict(task: dict[str, Any]) -> dict[str, Any]:
    """Prune a full task dictionary to essential scan fields only."""
    return {
        "id": task["id"],
        "title": task["title"],
        "status": task["status"],
    }


def slim_phase_dict(phase: dict[str, Any]) -> dict[str, Any]:
    """Prune a full phase dictionary to essential scan fields only."""
    return {
        "id": phase["id"],
        "title": phase["title"],
        "status": phase["status"],
    }


def local_is_same_phase(task_1: Any, task_2: Any) -> bool:
    """Helper to check if two tasks belong to the same phase."""
    from engram.models.task import get_effective_phase_title

    if task_1.phase_id and task_2.phase_id:
        return task_1.phase_id == task_2.phase_id
    return get_effective_phase_title(task_1) == get_effective_phase_title(task_2)
