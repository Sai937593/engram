# Implementation Plan - Phase 6.3

## Scope
Rewrite finish-gate regression tests so finish is blocked only by verification/worktree gates, not by missing or invalid `memory_review_outcome`.

## Files
- tests/test_services_workflow_finish.py
- tests/test_mcp_tools.py
- tests/test_workflow_redesign_phase_15_end_to_end.py
- tests/test_workflow_redesign_phase_5_regressions.py

## Planned changes
1. Update service-layer finish tests to assert success when `memory_review_outcome` is missing or invalid, while preserving existing verification and worktree blocking assertions.
2. Update MCP/tool-layer finish tests to remove any setup or assertions that still require `memory_review_outcome` as a prerequisite.
3. Update E2E workflow finish tests to prove a verified, clean task can finish without any memory-review update step.
4. Keep memory-related assertions only where they describe returned task fields, not finish eligibility.

## Verification
- Run focused tests:
  - `uv run pytest tests/test_services_workflow_finish.py tests/test_mcp_tools.py tests/test_workflow_redesign_phase_15_end_to_end.py tests/test_workflow_redesign_phase_5_regressions.py -q`
- Run workflow gate:
  - `engram_workflow_verify`

## Risks
- Legacy assertions may still assume `memory_review_outcome` is mandatory in specific E2E branches.
- Test fixtures may include incidental memory-review updates that hide missing-coverage gaps.

## Done criteria
- Finish regression coverage no longer fails for missing/invalid `memory_review_outcome`.
- At least one success-path test explicitly finishes after verify with no memory-review step.
- Verification and worktree cleanliness gate coverage remains intact.
