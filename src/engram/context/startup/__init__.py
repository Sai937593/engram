"""Startup context generation subpackage."""

from engram.context.startup.builders import (
    _build_guardrail_frame,
    _build_next_action,
    _build_phase_frame,
    _build_project_frame,
    _build_task_frame,
    _build_task_memory_candidates_frame,
)
from engram.context.startup.options import (
    CONTEXT_TRUNCATION_MARKER,
    STARTUP_HARD_CHAR_BUDGET,
    STARTUP_HARD_TOKEN_BUDGET,
    STARTUP_TARGET_CHAR_BUDGET_MAX,
    STARTUP_TARGET_CHAR_BUDGET_MIN,
    STARTUP_TARGET_TOKEN_BUDGET_MAX,
    STARTUP_TARGET_TOKEN_BUDGET_MIN,
    TOKEN_TO_CHAR_APPROX,
    StartupContextOptions,
    _compact_with_limit,
    _enforce_hard_budget,
    _render_section,
)
from engram.context.startup.orchestrator import (
    _resolve_default_startup_inputs,
    _task_matches_phase,
    build_startup_context,
)

__all__ = [
    "CONTEXT_TRUNCATION_MARKER",
    "STARTUP_HARD_CHAR_BUDGET",
    "STARTUP_HARD_TOKEN_BUDGET",
    "STARTUP_TARGET_CHAR_BUDGET_MAX",
    "STARTUP_TARGET_CHAR_BUDGET_MIN",
    "STARTUP_TARGET_TOKEN_BUDGET_MAX",
    "STARTUP_TARGET_TOKEN_BUDGET_MIN",
    "TOKEN_TO_CHAR_APPROX",
    "StartupContextOptions",
    "_compact_with_limit",
    "_enforce_hard_budget",
    "_render_section",
    "build_startup_context",
    "_resolve_default_startup_inputs",
    "_task_matches_phase",
    "_build_project_frame",
    "_build_phase_frame",
    "_build_task_frame",
    "_build_guardrail_frame",
    "_build_task_memory_candidates_frame",
    "_build_next_action",
]
