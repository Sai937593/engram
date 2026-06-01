# Implementation Plan - Phase 4.5 Verification Regression Coverage

## Scope
Add and/or adjust regression tests to lock final Phase 4 verification behavior across service, MCP, and end-to-end flows:
- missing active task precondition
- failed verify semantics (`is_verified` remains false)
- passing verify semantics (stages worktree and sets `is_verified` true)
- persistence/visibility of verification state through MCP and integration paths

## Planned Changes
1. Service coverage (`tests/test_services_workflow_verify.py`)
- Confirm/extend explicit assertions for:
  - no in-progress task -> `NO_TASK_IN_PROGRESS`
  - failed verify run keeps `Task.is_verified` false
  - successful verify run executes staging and sets `Task.is_verified` true
- Add narrow assertions only where final behavior is currently under-specified.

2. MCP coverage (`tests/test_mcp_tools.py`)
- Verify `engram_workflow_verify` output remains compact and deterministic for pass/fail.
- Ensure MCP-visible behavior aligns with service verification contract for active-task requirement and verification result semantics.

3. End-to-end coverage (`tests/test_workflow_redesign_phase_15_end_to_end.py`)
- Ensure at least one integration path exercises real staging behavior and verification persistence.
- Tighten assertions only around the Phase 4.5 contract; avoid unrelated refactors.

## Verification
Run:
- `uv run pytest tests/test_services_workflow_verify.py tests/test_mcp_tools.py tests/test_workflow_redesign_phase_15_end_to_end.py`

If any failures are unrelated or flaky, isolate and fix only blockers tied to this task scope.

## Out of Scope
- Service/CLI/MCP redesigns beyond regression coverage.
- New abstractions or broad cleanup in test modules.
