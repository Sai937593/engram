# Implementation Plan - Task 4ad16046

## Scope
Restrict workflow-start task selection so new execution starts only from `ready` tasks, while still resuming genuine `in-progress` work. When no ready tasks exist but draft tasks remain, return compact blocked guidance explaining that required task metadata must be completed first.

## Constraints and Boundaries
- One-task session only: execute only task `4ad16046`.
- No edits in `planning/`, `workflow/`, or `.github/`.
- Service layers must remain adapter-safe (no CLI/MCP adapter imports in services).
- Preserve Phase 11 minimal ready-gate behavior; do not add Phase 12 quality heuristics.

## Inputs to Use
- `src/engram/models/task/queries.py`
- `src/engram/services/workflow_helpers.py`
- `src/engram/services/workflow_service.py`
- `src/engram/services/workflow_formatter.py`
- `src/engram/context/startup/next_action.py`
- `src/engram/mcp/tools/workflow_tools.py`
- `tests/test_services_workflow_start_basic.py`
- `tests/test_services_workflow_helpers.py`
- `tests/test_mcp_tools.py`
- `tests/test_context.py`

## Planned Changes
1. Add explicit task-status counting/selection helpers so workflow-start logic can distinguish:
   - resumable `in-progress` work,
   - actionable `ready` work,
   - draft-only remaining work.
2. Keep resumption priority for real `in-progress` tasks, but ensure any non-resume new start path selects only `ready` tasks.
3. Introduce a draft-only blocked condition from start selection (service-level signal), then format a compact startup-blocked response with clear next action.
4. Update startup next-action wording so draft-only states tell Codex to complete minimum metadata and promote tasks to `ready`.
5. Add targeted tests for:
   - selecting/resuming in-progress tasks,
   - selecting ready tasks only for new starts,
   - blocked response when only draft tasks remain,
   - unchanged behavior for zero-task / all-done cases.

## Validation Plan
- Run: `uv run pytest tests/test_services_workflow_start_basic.py -q tests/test_mcp_tools.py -q tests/test_context.py -q tests/test_services_workflow_helpers.py -q`
- Run: `engram_workflow_verify`
- If verification fails, fix the first actionable issue and rerun verification.

## Out of Scope
- Any richer metadata-quality scoring (Phase 12).
- Changes unrelated to workflow-start/task-next selection.
- Any work on tasks other than `4ad16046` in this session.
