# Implementation Plan: Phase 4.4 - Surface verify gate details through MCP output

## Scope
- Update only MCP verify output formatting and related tests so failure responses include concise command/exit-code context from the service summary.
- Ensure pass responses explicitly state verification succeeded and changes were staged.
- Preserve existing behavior for non-verify workflow tools and existing error contracts (including `NO_TASK_IN_PROGRESS`).

## Files to touch
- `src/engram/mcp/tools/workflow_tools.py`
- `src/engram/services/workflow_formatter.py`
- `tests/test_mcp_tools.py`
- `tests/test_workflow_redesign_phase_15_end_to_end.py`

## Planned changes
1. Verify output wiring
- Keep `engram_workflow_verify` delegating to service-layer `verify_workflow` and continue passing `res["summary"]` into formatter details.
- Update pass `next_guidance` string so it explicitly states verification succeeded and staged changes are ready for finish.

2. Verify formatter wording
- Keep compact markdown contract (`# Verification Result`, single `## Details`, single `## Next action`).
- Ensure status wording and detail placement make failure context (including command and exit code already provided by service summary) directly visible without extra sections or verbose dumps.

3. Test updates
- Adjust MCP tool tests to assert the updated pass guidance text and unchanged compact structure.
- Adjust E2E verify assertions to match explicit pass wording and staged-changes phrasing.
- Keep existing assertions for failed output and `NO_TASK_IN_PROGRESS` behavior intact.

## Verification
- Run: `uv run pytest tests/test_mcp_tools.py -q`
- If needed for confidence after edits, run targeted E2E verify tests in `tests/test_workflow_redesign_phase_15_end_to_end.py`.

## Out of scope
- No changes to workflow finish/start contracts.
- No changes to service execution logic beyond output formatting/guidance text for this task.
- No unrelated refactors.
