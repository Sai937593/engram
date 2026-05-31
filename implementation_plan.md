# Implementation Plan - Task c63c5495

## Scope
Add regression coverage for the draft-to-ready execution path so Phase 11 lifecycle behavior remains stable: draft task creation, promotion to ready, blocked workflow start when only drafts remain, and successful selection/resumption once a ready task exists.

## Constraints and Boundaries
- One-task session only: execute only task `c63c5495`.
- No edits in `planning/`, `workflow/`, or `.github/`.
- Keep changes test-focused unless a missing test seam requires minimal production adjustment.
- Preserve Phase 11 minimal ready-gate behavior; do not introduce richer Phase 12 heuristics.

## Inputs to Use
- `tests/test_mcp_tools.py`
- `tests/test_services_workflow_start_basic.py`
- `tests/test_services_task.py`
- `tests/test_workflow_redesign_phase_5_regressions.py`

## Planned Changes
1. Review existing lifecycle coverage in the listed test modules and map gaps against the acceptance criteria.
2. Add/adjust tests validating draft task creation and promotion to `ready` with minimum required metadata.
3. Add/adjust workflow-start tests for blocked messaging when only `draft` tasks remain.
4. Add/adjust selection/resumption tests confirming a `ready` task is selected for new starts while true `in-progress` work is resumed.
5. Keep assertions deterministic and focused on observable service/MCP behavior, avoiding implementation-coupled expectations.

## Validation Plan
- Run targeted tests:
  - `uv run pytest tests/test_mcp_tools.py -q tests/test_services_workflow_start_basic.py -q tests/test_services_task.py -q tests/test_workflow_redesign_phase_5_regressions.py -q`
- Run full workflow verification: `engram_workflow_verify`
- If verification fails, fix the first actionable issue and rerun.

## Out of Scope
- Any non-regression feature work in workflow/task services.
- Any edits outside the accepted lifecycle regression scope.
- Work on tasks other than `c63c5495` in this session.
