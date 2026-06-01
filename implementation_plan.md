# Implementation Plan - Phase 11.2 (941014d1)

## Scope
Tighten regression tests for workflow verification behavior as the single local quality gate, focused on:
- `tests/test_services_workflow_verify.py`
- `tests/test_mcp_tools.py` (only workflow-verify related assertions if needed)

No production behavior changes unless a clear contract gap is discovered by tests.

## Target Behaviors
1. Active task requirement
- Verify the verify service errors clearly when no task is in progress.

2. Failure contract
- Verify failed verification persists a failed record with concise actionable details.
- Verify the active task remains `is_verified = false` after failure.

3. Success contract
- Verify successful verification runs `git add -A`.
- Verify success persists a passed record and sets active task `is_verified = true`.

4. Output stability
- Prefer assertions on stable semantic details (`status`, summary intent, actionable target, stage command evidence) rather than fragile formatting noise.

## Planned Edits
1. Review existing `tests/test_services_workflow_verify.py` coverage and add only missing assertions/cases for the above contracts.
2. If MCP verify output has a gap tied to this contract, add a minimal assertion in `tests/test_mcp_tools.py` within existing workflow verify tests.
3. Keep changes minimal and localized to regression tests.

## Verification Plan
1. Run targeted tests:
- `uv run pytest tests/test_services_workflow_verify.py`
- `uv run pytest tests/test_mcp_tools.py -k workflow_verify`
2. Run full workflow gate:
- `engram_workflow_verify`
3. If green, finish with:
- `engram_workflow_finish_and_commit`
