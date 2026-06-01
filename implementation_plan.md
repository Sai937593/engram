# Implementation Plan - Task a9b40139

## Scope
Expose MCP task lifecycle adapters for block, unblock, cancel, and retire actions by delegating to the task lifecycle service layer. Keep workflow_start/workflow_finish as the primary execution path.

## Files
- src/engram/mcp/tools/task_tools.py
- src/engram/mcp/tools/helpers.py
- src/engram/services/task/__init__.py (only if export surface needs adjustment)
- tests/test_mcp_tools.py
- tests/test_mcp_server.py

## Steps
1. Inspect existing task MCP tool patterns and helper response formatting for compact success/error output.
2. Add/update MCP handlers for task lifecycle actions that call service-layer lifecycle functions only (no DB access in MCP adapters).
3. Ensure deterministic mapping of service errors (invalid transition/missing refs) into compact, recovery-oriented MCP error responses.
4. Wire tool registration/exposure so the new lifecycle actions are available to Codex-facing MCP surfaces.
5. Add/adjust focused tests in MCP tool and server suites for success paths and invalid transition recovery guidance.
6. Run required verification tests:
   - uv run pytest tests/test_mcp_tools.py tests/test_mcp_server.py -q

## Constraints Checklist
- No direct mutation logic duplicated in MCP adapters.
- No service imports of MCP/CLI code.
- Keep outputs compact and actionable.
- Maintain lifecycle tools as secondary surfaces; do not bypass workflow loop.
