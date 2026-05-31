# Implementation Plan - Task a43434df (Phase 3.2)

## Scope
Add regression coverage proving normal MCP-first agent workflows remain CLI-independent, with focus on startup/current/context paths and retained MCP task/phase/memory tool paths.

## Current Findings
- `tests/test_mcp_server.py` already enforces banned imports for MCP modules only.
- `tests/test_services_context.py` enforces adapter-safe imports, but does not explicitly fail on runtime CLI module loading for wrapper flows.
- `tests/test_services_project.py` validates repo-local resolution behavior, but does not assert CLI modules are unnecessary/unused during normal resolution.
- `src/engram/mcp/server.py` currently calls `init_db()` directly before server run; this is acceptable if no CLI module is imported/called, but needs explicit regression checks.

## Planned Changes
1. `tests/test_mcp_server.py`
- Add assertions that MCP startup and core tool/resource registration paths do not import or invoke CLI command modules.
- Add actionable failure messages naming the forbidden module/function path when violated.

2. `tests/test_services_project.py`
- Add targeted tests proving `resolve_current_project()` succeeds on repo-local state with CLI modules intentionally blocked/unavailable.
- Add explicit test that unbound behavior still raises `PROJECT_NOT_BOUND` without any CLI bootstrap dependency.

3. `tests/test_services_context.py`
- Add runtime guard tests for startup/snapshot/handoff/task wrappers to ensure they resolve via services/context only, with CLI modules blocked.
- Keep checks read-only and repo-local, aligned with existing service behavior.

## Validation Plan
- Run targeted suite:
  - `pytest tests/test_mcp_server.py tests/test_services_project.py tests/test_services_context.py -q`
- If regressions appear in adjacent behavior, run:
  - `pytest tests/test_mcp_server.py tests/test_services_project.py tests/test_services_context.py tests/test_context.py -q`

## Out of Scope
- Implementing `engram_workflow_verify`, finish gating changes, or new lifecycle states.
- Refactoring CLI codepaths themselves unless required to restore existing behavior under these tests.
- Broad documentation updates.
