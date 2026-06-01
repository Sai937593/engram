# Implementation Plan: Expand regression coverage for batch creation (5cd2e288)

## Scope
Add regression tests to lock down batch task creation behavior across service and MCP layers without changing production behavior.

## Files to update
- tests/test_services_task.py
- tests/test_mcp_tools.py
- tests/test_mcp_server.py
- tests/test_mcp_startup_reliability.py

## Planned changes
1. Add/extend service-level tests for `create_many` success path:
   - Assert all requested tasks are created.
   - Assert response payload shape remains stable.

2. Add/extend service-level tests for invalid batch rejection:
   - Submit a mixed-validity batch.
   - Assert operation fails atomically.
   - Assert zero task rows are persisted after failure.

3. Add MCP tool contract regression coverage:
   - Verify `task_create_many` remains registered.
   - Verify stable success/error response shape exposed by MCP tool.

4. Add startup/server coverage as needed:
   - Guard against regressions where tool registration disappears.

## Verification
Run:
- `uv run pytest tests/test_services_task.py -q -k create_many`
- `uv run pytest tests/test_mcp_tools.py -q -k task_create_many`
- `uv run pytest tests/test_mcp_server.py -q -k task_create_many`
- `uv run pytest tests/test_mcp_startup_reliability.py -q -k task_create_many`

Then run a broader sanity pass if required by failures.

## Notes
- No changes under `planning/`, `workflow/`, or `.github/`.
- Keep changes test-focused and scoped to this task.
