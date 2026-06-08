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
        "DIRTY_WORKING_TREE": "Commit your changes using engram_workflow_finish_and_commit or stash them before starting a new task.",
        "INVALID_TASK_STATUS": "Use a valid task status (draft, ready, in-progress, done, blocked, or cancelled) and update using engram_task_update.",
        "READY_METADATA_INCOMPLETE": "Add or strengthen task description, acceptance criteria, and relevant_files, then retry engram_task_update with status=ready.",
        "TASK_METADATA_INCOMPLETE": "Add or strengthen task title, description, acceptance, phase_id, verification, and relevant_files/search_hints, then retry.",
        "PHASE_COMPLETION_BLOCKED": "Finish any unfinished tasks, let the phase reach review_pending, then retry engram_phase_complete.",
        "UNFINISHED_TASKS": "Finish or cancel the listed tasks, then retry engram_phase_complete after the phase is review_pending.",
        "PROJECT_NOT_BOUND": "Run engram_project_init to initialize Engram in this repository.",
        "UNRESOLVED_WORKSPACE": "Run git init first to initialize a git repository.",
        "INVALID_TASK_TRANSITION": "Use engram_task_get to inspect current status, then choose a valid lifecycle tool (engram_task_start, engram_task_done, engram_task_block, engram_task_unblock, engram_task_cancel, or engram_task_retire).",
        "INVALID_TASK_TRANSITION_TARGET": "Retry engram_task_unblock with target_status set to one of: draft, ready, or todo.",
        "TASK_ALREADY_IN_PROGRESS": "Complete, block, or cancel the current in-progress task before starting another one.",
        "INVALID_PHASE_REFERENCE": "Provide a non-empty phase ID, key, or exact phase title, then retry the phase lifecycle tool.",
        "PHASE_NOT_FOUND": "Run engram_phase_list to find a valid phase ID, key, or exact title, then retry.",
        "AMBIGUOUS_PHASE": "Use the exact phase ID instead of title to avoid ambiguous matches.",
        "INVALID_PHASE_VIEW": "Use view=compact or view=detail when calling engram_phase_list.",
        "INVALID_MEMORY_VIEW": "Use view=compact or view=detail when calling engram_memory_list.",
        "WORKFLOW_BRANCH_KEYS_MISSING": (
            "Set explicit project.plan_key and phase.key values before starting the task, or "
            "remove the phase assignment if this work is intentionally unphased."
        ),
        "DUPLICATE_PHASE_KEY": "Choose a different phase key before retrying engram_phase_create.",
        "DUPLICATE_TASK_KEY": "Choose a different task key before retrying engram_task_create.",
        "INVALID_PHASE_UPDATE": "Retry engram_phase_update using only string values for metadata fields.",
        "INVALID_PHASE_TRANSITION": "Use engram_phase_list to inspect the current phase status, then choose a valid lifecycle transition.",
        "TASK_NOT_VERIFIED": "Run engram_workflow_verify first, then retry engram_workflow_finish_and_commit.",
        "WORKTREE_HAS_UNSTAGED_CHANGES": "Stage all intended changes before running engram_workflow_finish_and_commit.",
        "WORKTREE_HAS_UNTRACKED_FILES": "Stage or remove untracked files before running engram_workflow_finish_and_commit.",
        "ACTIVE_PLAN_MISSING": "Create and activate a plan using engram_plan_create and engram_plan_activate.",
        "PLAN_NOT_FOUND": "List plans using engram_plan_list to find the correct plan ID or key.",
        "DUPLICATE_PLAN_KEY": "Choose a different plan key before retrying engram_plan_create.",
        "INVALID_PLAN_STATUS": "Use a valid plan status (draft, active, review_pending, done, archived, cancelled) and update using engram_plan_update.",
        "INVALID_PLAN_REFERENCE": "Provide a non-empty plan ID or key, then retry.",
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
    if exc.code in {"READY_METADATA_INCOMPLETE", "TASK_METADATA_INCOMPLETE"}:
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
    if exc.code not in {"READY_METADATA_INCOMPLETE", "TASK_METADATA_INCOMPLETE"}:
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

    if exc.code == "TASK_METADATA_INCOMPLETE":
        segments = ["Retry task creation or update with complete and strong metadata."]
    else:
        segments = ["Retry engram_task_update with status=ready after improving task metadata."]

    if missing:
        segments.append(f"Missing: {', '.join(missing)}.")
    if weak:
        segments.append(f"Strengthen: {', '.join(weak)}.")
    if reason_list:
        segments.append(f"Weak-field reasons: {'; '.join(reason_list)}.")
    return " ".join(segments)




def build_list_payload(
    *,
    filters: dict[str, Any],
    items: list[dict[str, Any]],
    populated_next_action: str,
    empty_next_action: str,
) -> dict[str, Any]:
    """Build a standard compact list payload for MCP list tools."""
    return {
        "ok": True,
        "filters": filters,
        "count": len(items),
        "items": items,
        "next_action": populated_next_action if items else empty_next_action,
    }


def build_task_list_payload(
    *,
    project_id: str,
    status: str | None = None,
    phase_ref: str | None = None,
    phase: str | None = None,
    scope: str | None = None,
    view: str | None = None,
) -> dict[str, Any]:
    """Build the standard task list response payload."""
    from engram.services.task import list_tasks, resolve_task_list_filters

    effective_phase_ref = phase_ref if phase_ref is not None else phase
    filters = resolve_task_list_filters(
        project_id=project_id,
        status=status,
        phase_ref=effective_phase_ref,
        scope=scope,
        view=view,
    )
    items = list_tasks(
        project_id=project_id,
        status=status,
        phase_ref=effective_phase_ref,
        scope=scope,
        view=view,
    )
    return build_list_payload(
        filters=filters,
        items=items,
        populated_next_action="Use engram_task_get <id> for full task details.",
        empty_next_action="Try scope=all to broaden the list.",
    )



