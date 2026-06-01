# Implementation Plan - Phase 12.3 (Task b041c5a3)

## Scope
Refine MCP-visible task update and workflow guidance so task-quality failures are compact, specific, and actionable when ready-promotion metadata is incomplete or weak.

## Files in scope
- src/engram/mcp/tools/helpers.py
- src/engram/mcp/tools/task_tools.py
- src/engram/mcp/tools/workflow_tools.py
- tests/test_mcp_tools.py

## Plan
1. Review current error rendering and guidance mapping for `READY_METADATA_INCOMPLETE` and related task-quality/status failures to identify where MCP responses are too generic.
2. Implement helper-level formatting updates so `EngramServiceError` payload details (for evaluated/missing/weak fields) are surfaced in concise, deterministic MCP output.
3. Adjust `engram_task_update` and/or workflow-start blocked messaging to point Codex to exact metadata fields to strengthen before retrying `status=ready`.
4. Add focused MCP tests that assert:
   - field-specific guidance appears for quality-gated ready promotion,
   - output remains compact and non-duplicative,
   - existing error behavior for unrelated codes is preserved.
5. Run targeted MCP tests, then run full `pytest` to confirm no regressions.

## Non-goals
- No service-layer validation logic redesign (Phase 12.2 already owns enforcement contract).
- No edits in `planning/`, `workflow/`, or `.github/`.
- No changes beyond this single Engram task.
