# Implementation Plan: Task afaa6364

## Scope
Expand regression coverage for workflow finish-and-commit boundaries without changing workflow design.

## Relevant constraints applied
- Keep changes focused to test coverage and expected outputs.
- Preserve compatibility: primary MCP finish tool is `engram_workflow_finish_and_commit` and alias `engram_workflow_finish` remains covered.
- Finish must require verified state and must not stage unstaged/untracked changes.
- Task transitions to done only after commit/push succeed.
- Avoid memory-review redesign changes (out of scope).

## Planned changes
1. Audit and rebaseline finish-related assertions in:
   - `tests/test_services_workflow_finish.py`
   - `tests/test_services_workflow_finish_meta.py`
   - `tests/test_mcp_tools.py`
   - `tests/test_workflow_redesign_phase_15_end_to_end.py`
   - `tests/test_workflow_redesign_phase_5_regressions.py`
2. Add or tighten service-level regressions for:
   - Not-verified blocking.
   - Unstaged changes blocking.
   - Untracked files blocking.
   - No implicit `git add -A` during finish.
   - Task status remains `in-progress` when commit or push fails.
3. Add or tighten MCP/end-to-end regressions for:
   - Primary tool naming (`engram_workflow_finish_and_commit`) plus wrapper alias compatibility.
   - Blocked finish messaging for verification and worktree gate failures.
   - Successful staged-only commit path.
4. Remove/replace legacy assertions that still imply finish performs staging or that old tool naming is primary.
5. Run focused tests, then broader targeted suite:
   - `uv run pytest -q tests/test_services_workflow_finish.py tests/test_services_workflow_finish_meta.py`
   - `uv run pytest -q tests/test_workflow_redesign_phase_5_regressions.py -k finish`
   - `uv run pytest -q tests/test_workflow_redesign_phase_15_end_to_end.py -k finish`
   - `uv run pytest -q tests/test_mcp_tools.py -k "workflow_finish or finish_and_commit"`

## Expected outcome
Regression coverage explicitly enforces the finish-and-commit boundary and prevents fallback to old staging/flow assumptions.
