# Implementation Plan - Task 7774e488 (Phase 8.2)

## Scope
Enforce the verification gate in `workflow_finish` output behavior so missing/failed/stale verification blocks finish with compact markdown and exactly one `## Next action` section instructing Codex to run or rerun workflow verification. Keep successful finish output concise and do not auto-start the next task.

## Constraints and Boundaries
- One-task session only: execute only task `7774e488`.
- Keep scope limited to finish-time verification gate and MCP finish output.
- Do not add memory review gates, stale-memory policies, or phase transition automation.
- Service modules must remain adapter-safe.
- No-touch directories: `planning/`, `workflow/`, `.github/`.

## Investigation Plan
1. Confirm current finish-time eligibility behavior and emitted error codes/messages:
- `src/engram/services/workflow_service.py`
- `src/engram/services/workflow_verification_service.py`

2. Confirm formatting helpers for blocked/success finish responses:
- `src/engram/services/workflow_formatter.py`

3. Confirm MCP tool mapping from service errors to final finish response:
- `src/engram/mcp/tools/workflow_tools.py`

## Planned Changes
1. Ensure blocked finish states (missing/failed/stale) are surfaced as compact markdown via `format_finish_blocked` with:
- task context line
- compact reason line
- exactly one `## Next action` section
- next action text explicitly telling Codex to run or rerun `engram_workflow_verify`

2. Keep verification gate execution before any git side effects (`git add/commit/push`) and preserve existing behavior for successful eligible finishes.

3. Keep successful finish response concise via `format_finish_success`, with no automatic workflow start behavior.

4. Add or update focused tests for MCP finish output covering:
- missing verification -> blocked format + next action
- failed verification -> blocked format + next action
- stale verification -> blocked format + next action
- successful eligible finish -> concise success format unchanged

## Validation Plan
- Run targeted workflow tool/service tests for finish and formatter behavior.
- Run any affected tests for workflow verification eligibility integration.
- Confirm zero test failures before invoking `engram_workflow_finish`.

## Out of Scope
- Memory review gates or broader task readiness policies.
- New automation for PR/phase transitions.
- Refactoring unrelated workflow command surfaces.
