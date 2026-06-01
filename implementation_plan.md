# Implementation Plan - Add Primary finish_and_commit MCP Tool (Task 06e0af06)

## Scope
Expose `engram_workflow_finish_and_commit` as the preferred MCP finish tool while keeping `engram_workflow_finish` working during transition. Update tool-facing guidance text to prefer the new name. Keep workflow start/verify behavior unchanged and avoid adding staging behavior in the tool layer.

## Planned Changes
1. Update workflow tool registration in `src/engram/mcp/tools/workflow_tools.py`
- Register a new MCP handler: `engram_workflow_finish_and_commit(commit_type: str | None = None)`.
- Keep existing finish execution path by delegating to `engram.mcp.tools.finish_workflow(...)` with unchanged arguments.
- Reuse the same success and blocked formatting behavior currently used by `engram_workflow_finish`.
- Keep `engram_workflow_finish` as a deprecated wrapper/alias that calls the same implementation.

2. Centralize finish handler behavior to avoid duplication
- Extract shared async finish logic into an internal helper in `workflow_tools.py` (or equivalent minimal private function) so both tool names stay behaviorally identical.
- Ensure blocked guidance and success next-actions prefer `engram_workflow_finish_and_commit`.

3. Update finish blocked helper guidance in `src/engram/mcp/tools/workflow_tool_helpers.py`
- Change next-action strings to instruct:
  - rerun verify, then call `engram_workflow_finish_and_commit`
  - record `memory_review_outcome`, then call `engram_workflow_finish_and_commit`
  - resolve staging/worktree issues, then call `engram_workflow_finish_and_commit`

4. Update exports/wiring in `src/engram/mcp/tools/__init__.py` only if needed
- Preserve existing service wiring and avoid adding tool-layer staging logic.
- Keep changes minimal and limited to naming/wiring compatibility.

5. Update tests
- `tests/test_mcp_tools.py`
  - assert both `engram_workflow_finish_and_commit` and `engram_workflow_finish` are registered.
  - validate new tool name returns expected success and blocked markdown behavior.
  - update expected next-action strings to prefer `engram_workflow_finish_and_commit`.
- `tests/test_mcp_server.py`
  - adjust registration expectations if they assert exact tool set.

## Verification
- Run focused tests:
  - `uv run pytest tests/test_mcp_tools.py tests/test_mcp_server.py`
- Then run workflow verify gate:
  - `engram_workflow_verify`

## Out Of Scope
- Removing `engram_workflow_finish` entirely.
- Changing workflow start or verify semantics.
- Service-layer refactors unrelated to MCP tool registration/guidance.
