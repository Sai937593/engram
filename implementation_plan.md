# Implementation Plan - Phase 12.4 (Task 121be327)

## Scope
Add regression coverage that locks the draft -> fix metadata -> ready loop for task-quality validation, including failure-state assertions and successful recovery.

## Files in scope
- tests/test_services_task.py
- tests/test_mcp_tools.py
- tests/test_services_workflow_start_basic.py
- tests/test_workflow_redesign_phase_5_regressions.py

## Plan
1. Inspect existing Phase 12.1-12.3 tests and fixtures to identify current ready-promotion validation assertions and where draft repair coverage is missing.
2. Add service-level regression tests that verify:
   - draft task creation/update can fail `status=ready` with weak or missing metadata,
   - failure payload exposes deterministic quality details,
   - metadata repair enables successful transition to `ready`.
3. Add MCP-facing regression assertions (if needed) to ensure surfaced guidance remains stable for the same failure/recovery loop.
4. Run focused test modules first, then execute full `pytest` to validate no regressions.
5. If tests expose unstable assumptions, adjust only test expectations/fixtures needed for this task without changing Phase 12 enforcement behavior.

## Non-goals
- No redesign of service validation heuristics (already covered by earlier Phase 12 tasks).
- No edits in `planning/`, `workflow/`, or `.github/`.
- No work on additional Engram tasks in this session.
