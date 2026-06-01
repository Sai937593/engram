# Implementation Plan - Phase 8.3 Memory Batch MCP Tools

## Scope
Implement two MCP memory lifecycle tools:
- `engram_memory_update_many`
- `engram_memory_delete_many`

No generic batch mutate tool will be added.

## Files to Change
- `src/engram/mcp/tools/memory_lifecycle_tools.py`
- `src/engram/mcp/tools/__init__.py` (only if exports require updates)
- `src/engram/mcp/server.py` (only if direct registration changes are required)
- `src/engram/mcp/schemas.py` (only if lightweight tool schema mapping is already expected by current patterns)
- `tests/test_mcp_tools.py`
- `tests/test_mcp_server.py` (only if registration assertions need extension)

## Planned Implementation
1. Add `engram_memory_update_many` MCP handler in `memory_lifecycle_tools.py`.
2. Add `engram_memory_delete_many` MCP handler in `memory_lifecycle_tools.py`.
3. Keep argument contracts simple and deterministic:
   - Require non-empty batch payload input.
   - Raise clear validation errors via existing `ValidationError` path for invalid/missing inputs.
   - Avoid partial mutation by delegating atomic behavior to underlying service methods.
4. Delegate both tools to existing service-layer batch APIs (Phase 8.1/8.2 dependency) through current project resolution.
5. Return compact success payloads with actionable summary fields (counts/ids/outcome) rather than verbose records.
6. Preserve existing lifecycle tools and behavior unchanged.

## Planned Tests
1. Registration tests:
   - Assert both tool names are present after `register_tools(server)`.
2. MCP behavior tests for each new tool:
   - Happy path returns `ok: true` and compact summary fields.
   - Invalid input returns clear validation error payload.
   - Service error path is surfaced via `_respond_error` with no raw traceback.
3. If needed, monkeypatch service functions to confirm MCP tool delegates through service API boundaries.

## Verification
- Run focused tests first:
  - `uv run pytest tests/test_mcp_tools.py -k "memory_update_many or memory_delete_many or register_tools"`
- Run broader MCP checks if needed:
  - `uv run pytest tests/test_mcp_server.py tests/test_mcp_tools.py`
- Then run workflow verification gate:
  - `engram_workflow_verify`

## Non-goals
- No CLI changes.
- No memory model/schema redesign.
- No generic batch mutation MCP surface.
- No unrelated refactoring.
