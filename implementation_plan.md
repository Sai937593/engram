# Implementation Plan - Task b4ccfe48 (Phase 7.2)

## Scope
Implement `engram_workflow_verify` service execution flow in the workflow service so it runs repository-local quality checks via the established Python workflow helpers, records pass/fail verification state, and returns concise failure output centered on the first actionable fix target.

## Constraints and Boundaries
- One-task session only: execute only task `b4ccfe48`.
- Phase boundary: do not add `engram_workflow_finish` gating, stale-result enforcement, or memory-review requirements.
- No-touch directories: `planning/`, `workflow/`, `.github/`.
- Service safety: `src/engram/services` must remain adapter-safe and must not import Click, Rich, CLI modules, subprocess, or MCP adapter code.
- Keep concise and actionable verify output; avoid long raw log dumps.

## Investigation Plan
1. Inspect current verify-related service API and result contracts:
- `src/engram/services/workflow_service.py`
- `src/engram/services/workflow_helpers.py`
- `src/engram/services/errors.py`

2. Inspect existing verification-state persistence hooks from prior phase:
- workflow verify state record/read helpers
- current schemas/types used by service layer

3. Inspect current tests and expected output style:
- `tests/test_services_workflow_verify.py`

## Planned Changes
1. Service execution entrypoint:
- Add or complete workflow-service logic for `engram_workflow_verify` to invoke local quality checks through existing workflow helpers.
- Ensure execution path is service-only and adapter-safe.

2. Verification recording:
- Persist verification outcomes for both passing and failing runs using existing verification-state recording mechanisms.
- Ensure recorded data remains usable for later lookup/freshness features (without implementing freshness enforcement now).

3. Concise failure shaping:
- Map failing command/test output into a compact summary with clear pass/fail status.
- Derive and surface the first actionable fix target when possible (e.g., first failing test/file/check) instead of returning full logs.

4. Tests:
- Add/update service tests to cover:
  - pass flow executes checks and records success
  - fail flow records failure and returns concise actionable message
  - output shape remains compact and deterministic

## Validation Plan
- Run targeted test module first:
- `tests/test_services_workflow_verify.py`
- If needed, run additional directly related service tests.
- Ensure zero failures for touched tests before `engram_workflow_finish`.

## Out of Scope
- Blocking `engram_workflow_finish` on verification state.
- Stale-verification enforcement logic.
- Memory-review enforcement.
- Unrelated workflow command/service refactors.
