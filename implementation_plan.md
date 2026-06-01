# Implementation Plan - Phase 7.1

## Scope
Add a compact, project-scoped memory read interface by wiring `engram_memory_list` and adapting `engram_memory_get` output defaults, while keeping richer internal retrieval paths intact for existing callers.

## Files
- src/engram/services/memory_service.py
- src/engram/services/serializers.py
- src/engram/mcp/tools/memory_tools.py
- src/engram/mcp/tools/memory_lifecycle_tools.py
- tests/test_services_memory.py
- tests/test_mcp_tools.py

## Planned changes
1. Inspect current service read functions and serializer entry points to identify where list/get response shape is defined and where internal rich fields are consumed.
2. Add or adapt a service-level list path that returns project-scoped memories for MCP tool usage without requiring search flow inputs.
3. Register or expose `engram_memory_list` in MCP tools and route it through the service list path.
4. Define/update default compact serializer shape for list/get to foreground memory id, title, content (or preview), and timestamps.
5. Keep richer retrieval data available via existing internal code paths so current non-agent-facing callers are not broken.
6. Add/update focused tests for service and MCP tool behavior for list/get compact output and registration.

## Verification
- Run focused tests:
  - `uv run pytest tests/test_services_memory.py tests/test_mcp_tools.py -q`
- Run workflow gate:
  - `engram_workflow_verify`

## Risks
- Existing tests or callers may currently assert advanced metadata fields in default responses.
- Serializer changes could unintentionally affect lifecycle tool outputs if shared serializer functions are used broadly.

## Done criteria
- `engram_memory_list` is callable and returns project-scoped memories.
- Default list/get output is compact and readable with identity, title, content/content preview, and timestamps.
- Advanced lifecycle metadata is not foregrounded in normal agent-facing output.
- Existing richer internal retrieval callers continue to function.
