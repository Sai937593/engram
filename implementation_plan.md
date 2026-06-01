# Implementation Plan - Phase 11.3 (f0cef447)

## Scope
Harden finish-boundary tests for `engram_workflow_finish_and_commit` without changing production behavior unless a concrete contract gap is exposed by tests.

Primary files:
- `tests/test_services_workflow_finish.py`
- `tests/test_workflow_redesign_phase_5_regressions.py`
- `tests/test_mcp_tools.py`

No-touch for this task unless strictly required:
- `planning/`
- `workflow/`
- `.github/`

## Target Behaviors
1. Verification gate
- Finish blocks when the active task is not verified (`TASK_NOT_VERIFIED`).

2. Worktree cleanliness gate
- Finish blocks when unstaged changes exist (`WORKTREE_HAS_UNSTAGED_CHANGES`).
- Finish blocks when untracked files exist (`WORKTREE_HAS_UNTRACKED_FILES`).

3. Boundary ownership
- Finish must not run staging (`git add -A`) and only commits/pushes pre-staged work.

4. Completion ordering
- Task is marked `done` only after commit/push succeeds.

## Planned Edits
1. Audit existing finish tests for explicit assertions of each acceptance item.
2. Add or tighten only missing assertions/cases in the three target test files.
3. Prefer service-level assertions for git-call ordering and MCP-level assertions for user-facing blocked behavior.
4. Keep edits localized; avoid unrelated refactors or output-format churn.

## Verification Plan
1. Run required task verification command:
- `uv run pytest tests/test_services_workflow_finish.py tests/test_workflow_redesign_phase_5_regressions.py tests/test_mcp_tools.py -q -k "finish and commit"`
2. If failures appear, fix only finish-boundary regressions and rerun the same command until green.
3. After tests pass, run `engram_workflow_verify`.
4. If verify succeeds, run `engram_workflow_finish_and_commit`.
