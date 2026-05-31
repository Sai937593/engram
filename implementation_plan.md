# Implementation Plan - Task 5b0dc009 (Phase 8.1)

## Scope
Add service-layer evaluation logic for `engram_workflow_finish` eligibility based on the active task's latest verification record. Classification must be deterministic with states: `passed`, `missing`, `failed`, `stale`. Keep this task strictly to state lookup and evaluation helpers.

## Constraints and Boundaries
- One-task session only: execute only task `5b0dc009`.
- Do not change finish response formatting in MCP/CLI layers.
- Do not add memory-review or broader readiness gates.
- Service modules must remain adapter-safe (no Click/Rich/MCP adapter imports).
- No-touch directories: `planning/`, `workflow/`, `.github/`.
- Keep changes focused to service/helper logic and unit tests for that logic.

## Investigation Plan
1. Inspect finish path and helper extension points:
- `src/engram/services/workflow_service.py`
- `src/engram/services/workflow_helpers.py`

2. Inspect verification persistence/lookup APIs and record shape:
- `src/engram/services/workflow_verification_service.py`
- verification-related tests under `tests/`

3. Confirm whether existing repo-local evidence (timestamps and git state) can support stale detection deterministically without CLI coupling.

## Planned Changes
1. Add verification eligibility resolver in service layer:
- Resolve active in-progress task.
- Fetch latest verification record for that task.
- Return structured state result with deterministic reason code and message.

2. Implement stale-after-relevant-changes check using repo-local evidence:
- Compare latest verification timestamp with relevant post-verification repo/task change evidence.
- Keep algorithm deterministic and dependency-light.

3. Wire eligibility evaluation helper for finish-time use:
- Expose helper(s) callable by `finish_workflow` without changing current user-facing formatting in this task.

4. Add/extend focused tests:
- `missing`: no verification record.
- `failed`: latest record is failed.
- `passed`: latest record is passed and not stale.
- `stale`: latest record passed but invalidated by relevant subsequent changes.
- Deterministic reason assertions for each state.

## Validation Plan
- Run targeted tests for workflow services and verification logic.
- Run any impacted finish-workflow tests.
- Ensure no regressions in existing workflow verification tests.

## Out of Scope
- Editing finish output rendering or MCP markdown formatting.
- Introducing new workflow policies unrelated to verification eligibility.
- Completing phase transition or PR orchestration work.
