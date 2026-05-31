# Implementation Plan - Task 17692daf (Phase 9.5)

## Scope
Add regression coverage for memory review outcome recording and finish-time gating across service and MCP paths. Cover missing outcome blocking, valid outcomes, invalid outcome rejection, and the no-memory-change path.

## Constraints and Boundaries
- One-task session only: execute only task `17692daf`.
- Test-focused changes only unless a test exposes a true product bug in-scope.
- Preserve service/adapter boundaries (no CLI/MCP imports in `src/engram/services`).
- No-touch directories: `planning/`, `workflow/`, `.github/`.

## Investigation Plan
1. Review existing memory review assertions in:
- `tests/test_services_workflow_finish.py`
- `tests/test_mcp_tools.py`
- `tests/test_workflow_redesign_phase_5_regressions.py`

2. Inspect implementation contracts for allowed outcomes and update path:
- `src/engram/models/task.py`
- `src/engram/services/workflow_service.py`
- `src/engram/mcp/tools/workflow_tools.py`

3. Identify exact missing scenarios versus acceptance and add minimal tests.

## Planned Changes
1. Service regressions (`tests/test_services_workflow_finish.py`):
- Add/extend test coverage for all valid `memory_review_outcome` enum values passing finish gate.
- Add/extend explicit invalid outcome rejection coverage at update/model/service boundary.
- Keep missing-outcome block assertion deterministic (`MEMORY_REVIEW_OUTCOME_MISSING`).

2. MCP regressions (`tests/test_mcp_tools.py`):
- Add/extend `engram_task_update` coverage for valid outcomes and invalid outcome rejection through MCP handler contract.
- Assert no-memory-change path is accepted when outcome is `no_change` and reflected in response.

3. End-to-end contract regressions (`tests/test_workflow_redesign_phase_5_regressions.py`):
- Add/extend finish-gate E2E flow to include `no_change` success path and ensure compact output remains stable.
- Keep one `## Next action` section and deterministic blocked guidance.

## Validation Plan
- Run targeted tests:
- `uv run pytest tests/test_services_workflow_finish.py -q`
- `uv run pytest tests/test_mcp_tools.py -q`
- `uv run pytest tests/test_workflow_redesign_phase_5_regressions.py -q`
- If all pass, run `engram_workflow_verify` before finish.

## Out of Scope
- Changing memory review outcome taxonomy.
- Refactoring unrelated workflow formatting.
- Multi-task or phase-transition execution.
