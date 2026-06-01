# Implementation Plan - Phase 4.2 (08c04dcc)

## Scope
Update verify failure recording so the first failing command persists:
- command string
- exit code
- concise output tail

while keeping active task unverified and ensuring failure path does not stage files.

## Files to change
- src/engram/services/workflow_verify_service.py
- tests/test_services_workflow_verify.py

## Planned changes
1. Adjust failure details formatter in `workflow_verify_service.py` to include:
- failing command string
- process exit code
- concise tail from combined stdout/stderr

2. Keep existing failure summary behavior concise and deterministic, preserving actionable target extraction.

3. Confirm failure path continues to persist `passed=False` via existing record call (which keeps task unverified semantics).

4. Add/update tests in `tests/test_services_workflow_verify.py` to assert:
- failure details contain command, exit code, and output tail
- persisted verification status is `failed`
- no staging side effects are introduced by verify failure behavior

## Verification
Run:
- `uv run pytest tests/test_services_workflow_verify.py -q`
- `engram_workflow_verify`

## Notes
No changes are planned to finish/staging logic outside verify failure record formatting and associated tests.
