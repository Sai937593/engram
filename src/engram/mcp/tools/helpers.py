"""Shared helper functions for MCP tools."""

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
        "INVALID_TASK_STATUS": "Use a valid task status (draft, ready, in-progress, done, blocked, or cancelled) and update using engram_task_update.",
        "READY_METADATA_INCOMPLETE": "Add or strengthen task description, acceptance criteria, and relevant_files, then retry engram_task_update with status=ready.",
        "PHASE_COMPLETION_BLOCKED": "Complete all unfinished tasks in the phase using engram_task_done, or update/cancel them using engram_task_update before completing the phase.",
        "UNFINISHED_TASKS": "Complete all unfinished tasks in the phase using engram_task_done, or update/cancel them using engram_task_update before completing the phase.",
        "PROJECT_NOT_BOUND": "Run engram_project_init to initialize Engram in this repository.",
        "UNRESOLVED_WORKSPACE": "Run git init first to initialize a git repository.",
    }

    details = _compact_error_details(exc)
    fix_val = _resolve_error_fix(exc, known_fixes)

    resp_dict: dict[str, Any] = {
        "ok": False,
        "error": exc.code,
        "message": exc.message,
    }
    if details:
        resp_dict["details"] = details
    if fix_val:
        resp_dict["fix"] = fix_val

    return _respond(resp_dict)


def _compact_error_details(exc: EngramServiceError) -> dict[str, Any]:
    """Return compact, deterministic detail payload for actionable MCP errors."""
    if not exc.details:
        return {}
    if exc.code == "READY_METADATA_INCOMPLETE":
        keys = ("evaluated_fields", "missing_fields", "weak_fields", "weak_field_reasons")
        return {k: exc.details[k] for k in keys if k in exc.details}
    if exc.code == "INVALID_TASK_STATUS":
        keys = ("status", "allowed_statuses")
        return {k: exc.details[k] for k in keys if k in exc.details}
    return dict(exc.details)


def _resolve_error_fix(exc: EngramServiceError, known_fixes: dict[str, str]) -> str | None:
    """Prefer explicit fix; otherwise derive deterministic, field-specific guidance."""
    if getattr(exc, "fix", None):
        return exc.fix
    if exc.code != "READY_METADATA_INCOMPLETE":
        return known_fixes.get(exc.code)

    missing = sorted(
        str(v) for v in exc.details.get("missing_fields", []) if isinstance(v, str) and v.strip()
    )
    weak = sorted(
        str(v) for v in exc.details.get("weak_fields", []) if isinstance(v, str) and v.strip()
    )
    reasons = exc.details.get("weak_field_reasons", {})
    reason_list: list[str] = []
    if isinstance(reasons, dict):
        for field in weak:
            reason = reasons.get(field)
            if isinstance(reason, str) and reason.strip():
                reason_list.append(f"{field} ({reason.strip()})")

    segments = ["Retry engram_task_update with status=ready after improving task metadata."]
    if missing:
        segments.append(f"Missing: {', '.join(missing)}.")
    if weak:
        segments.append(f"Strengthen: {', '.join(weak)}.")
    if reason_list:
        segments.append(f"Weak-field reasons: {'; '.join(reason_list)}.")
    return " ".join(segments)


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
