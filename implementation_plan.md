# Implementation Plan - Phase 7.4

## Scope
Add focused regression tests that lock the simplified memory interface contract across MCP tool export and default agent-facing payloads for `engram_memory_list`, `engram_memory_get`, `engram_memory_create`, `engram_memory_update`, and `engram_memory_delete`, while preserving existing retrieval/startup behavior that uses internal metadata.

## Files
- tests/test_mcp_server.py
- tests/test_services_memory.py
- tests/test_context.py
- tests/test_memory_retrieval_fts_retriever.py
- src/engram/mcp/tools/memory_tools.py (read-only unless tests expose a gap)
- src/engram/mcp/tools/memory_lifecycle_tools.py (read-only unless tests expose a gap)
- src/engram/services/serializers.py (read-only unless tests expose a gap)

## Planned changes
1. Extend MCP server/toolset regression coverage to assert the expected simplified memory tool surface remains exported.
2. Add or update list/get output assertions so default compact responses exclude lifecycle-heavy fields (for example: `level`, `scope`, `always_include`, `superseded_by`) unless explicitly intended.
3. Add create/update/delete input-path tests that validate simplified inputs and guard against accidental re-expansion of required lifecycle-oriented parameters.
4. Confirm retrieval/startup regressions remain covered by current tests; add only minimal assertions if a coverage hole is identified.
5. Keep production code unchanged unless a test reveals a true contract mismatch that must be fixed to satisfy acceptance criteria.

## Verification
- Run targeted tests during implementation:
  - `uv run pytest tests/test_mcp_server.py`
  - `uv run pytest tests/test_services_memory.py`
  - `uv run pytest tests/test_context.py`
  - `uv run pytest tests/test_memory_retrieval_fts_retriever.py`
- Run workflow verification gate:
  - `engram_workflow_verify`

## Risks
- Existing fixtures may include metadata-rich objects; assertions must focus on default agent-facing serialized payloads, not internal model rows.
- Tool registration tests can become brittle if they overfit ordering instead of set membership.
- Startup/retrieval regressions may be indirectly affected by serializer-level expectations.

## Done criteria
- Regression tests cover simplified memory tool export and default list/get/create/update/delete contract behavior.
- Tests fail if lifecycle-heavy fields leak into default compact agent-facing outputs unexpectedly.
- Retrieval/startup metadata-dependent behavior remains covered and passing.
- `engram_workflow_verify` passes with no failures.
