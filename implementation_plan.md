# Implementation Plan - Phase 4.3 (d406d721)

## Scope
Update verify success behavior so staging and task verification state are owned by
`verify_workflow` after all target commands pass:
- run `git add -A` only on all-pass
- persist active task `is_verified = true`
- make success result explicitly indicate verified-and-staged behavior

Failure behavior from Phase 4.2 must remain unchanged.

## Files to change
- src/engram/services/workflow_verify_service.py
- tests/test_services_workflow_verify.py

## Planned changes
1. In `verify_workflow`, keep the existing per-command execution loop and early return on first failure unchanged.
2. After the loop succeeds, run `git add -A` in `repo_path` via subprocess and treat staging failure as verification failure with compact details.
3. Persist `is_verified = true` for the active task only after successful command execution and successful staging.
4. Update success `summary` and `details` payload to explicitly communicate that verification passed, files were staged, and task verification state was persisted.
5. Extend service tests to assert:
- success path invokes `git add -A` after the check commands
- success path persists `is_verified = true`
- success payload/details mention verified-and-staged semantics
- failure path still does not stage files and keeps task unverified

## Verification
Run:
- `uv run pytest tests/test_services_workflow_verify.py -q`
- `engram_workflow_verify`

## Notes
No workflow redesign changes outside this scoped verify behavior update.
