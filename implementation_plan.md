# Implementation Plan - Phase 11.4 (ee966963)

## Scope
Tighten tests for the simplified agent-facing memory interface, focusing on CRUD via service/MCP paths and explicit batch validation behavior for `engram_memory_update_many` and `engram_memory_delete_many`.

## Findings from current state
- `tests/test_services_memory.py` already covers service-level CRUD plus batch update/delete atomicity and validation.
- MCP batch tool wrappers in `src/engram/mcp/tools/memory_lifecycle_tools.py` add argument-level validation (`entries`/`memory_refs` required) and response shaping that is not yet directly asserted by dedicated tool tests.

## Planned changes
1. Inspect existing MCP tool tests to identify coverage gaps for:
   - `engram_memory_list`, `engram_memory_get`, `engram_memory_create`, `engram_memory_update`, `engram_memory_delete`
   - `engram_memory_update_many`, `engram_memory_delete_many` required-arg and invalid-payload paths.
2. Add focused tests (likely in MCP tool test module) to validate:
   - Missing `entries` / `memory_refs` return deterministic validation errors.
   - Invalid batch payloads fail clearly.
   - Batch operations remain all-or-nothing for invalid inputs through the MCP entrypoints.
3. Keep assertions aligned with compact agent-facing output contracts (`ok`, summary counts/ids, concise error codes/messages/details).
4. Run targeted unit tests for modified files.
5. Run `engram_workflow_verify` to execute repo-local gates and stage changes.
6. Run `engram_workflow_finish_and_commit` to finalize task.

## Non-goals
- No behavior changes to memory service logic unless tests reveal a real defect.
- No lifecycle semantics expansion beyond simplified CRUD/batch scope.
