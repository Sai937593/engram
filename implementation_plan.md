# Implementation Plan - Phase 7.2

## Scope
Simplify the agent-facing memory CRUD contract so routine `engram_memory_create`, `engram_memory_update`, and `engram_memory_delete` usage does not require explicit memory governance fields (type/scope/level/tags/always_include/supersede semantics), while preserving valid stored schema values and compatibility for existing internal flows.

## Files
- src/engram/mcp/tools/memory_tools.py
- src/engram/mcp/tools/memory_lifecycle_tools.py
- src/engram/services/memory_service.py
- src/engram/services/memory_update_support.py
- src/engram/models/memory/helpers.py
- tests/test_services_memory.py
- tests/test_mcp_tools.py

## Planned changes
1. Define a simplified create contract at MCP/service boundary centered on required `content` (and optional `title`) with deterministic defaults for type, scope, and level.
2. Keep backward compatibility by accepting advanced fields as optional overrides, but stop requiring them in normal create/update paths.
3. Add a dedicated service-layer normalizer for create defaults so all call paths produce valid schema values without tool-side duplication.
4. Update `engram_memory_update` contract to accept straightforward field edits (especially content/title) without requiring callers to construct broad governance update payloads.
5. Ensure `engram_memory_delete` remains deterministic and safe via existing project-scoped reference resolution.
6. Update focused tests for simplified CRUD behavior and backward-compatible advanced-field acceptance.
7. Keep demote/supersede tools callable but avoid routing normal edit guidance through them.

## Verification
- Run focused tests:
  - `uv run pytest tests/test_services_memory.py tests/test_mcp_tools.py -q`
- Run workflow gate:
  - `engram_workflow_verify`

## Risks
- Existing tests may assert previous required-argument behavior for create/update.
- Default level assignment for project-scope memories must remain aligned with model validation rules.
- Contract simplification must not break legacy callers passing full advanced payloads.

## Done criteria
- `engram_memory_create` can be called with a simplified argument set focused on memory content.
- `engram_memory_update` supports straightforward edits without requiring demote/supersede workflow for routine updates.
- `engram_memory_delete` behavior remains deterministic and project-scoped.
- Stored records continue to satisfy scope/level/type validation and retrieval expectations.
