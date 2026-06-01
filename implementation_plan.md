# Implementation Plan - Finish Preflight Refactor (Task 3dd594b9)

## Scope
Refactor finish preflight logic so commit/push only proceed when explicit checks pass. Keep current memory-review gate behavior unchanged. Remove implicit staging side effect from finish.

## Planned Changes
1. Update finish preflight in `src/engram/services/workflow_service.py`
- Ensure finish fails early when there is no active `in_progress` task.
- Require active task verification state (`is_verified`) before any git commit path.
- Keep existing verification-eligibility checks that ensure verification is still valid.
- Add explicit worktree preflight checks after verification:
  - block if unstaged changes exist
  - block if untracked files exist
- Remove `git add -A` from finish so only already-staged content is committed.
- Keep task status unchanged (`in_progress`) for all preflight and git-operation failures.

2. Adjust helper usage as needed
- Reuse existing workflow helper/service utilities where available.
- Keep service-layer boundaries intact (no CLI/MCP adapter leakage).

3. Update tests
- `tests/test_services_workflow_finish.py`:
  - add/adjust coverage for no active in-progress task
  - add/adjust coverage for unverified active task
  - add/adjust coverage for unstaged/untracked blocking behavior
  - assert no implicit staging side effect in finish path
  - assert task remains in progress on failures
- `tests/test_services_workflow_finish_meta.py`:
  - update assertions only if commit resolution/phase completion expectations change due to preflight ordering

## Verification
Run focused tests first:
- `uv run pytest tests/test_services_workflow_finish.py tests/test_services_workflow_finish_meta.py`

Then run workflow verification gate:
- `engram_workflow_verify`

If failures appear, fix only scope-related issues and rerun until green.

## Out Of Scope
- Memory-review gate redesign (Phase 6+ work).
- Unrelated workflow/CLI refactors.
