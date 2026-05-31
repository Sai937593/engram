# Implementation Plan - Task 2.4 (4b1a8e06)

## Scope
Add/adjust regression tests only to prove MCP-first initialization and diagnostics across fresh workspaces. No product-scope expansion.

## Observed Gap vs Acceptance
Existing tests cover:
- `engram_project_init` success and unbound error behavior.
- `engram_project_current` actionable uninitialized behavior.
- diagnostics healthy/misconfigured/unresolved states.

What remains to prove explicitly:
- Same MCP handlers work across multiple fresh repo workspaces in one test flow (workspace-based behavior, no per-project command changes).
- End-to-end repo lifecycle in MCP terms: fresh repo -> init -> current/diagnostics ready.
- Explicit regression check that normal init/status flow does not rely on CLI commands.

## Planned Changes
1. `tests/test_mcp_tools.py`
- Add a multi-workspace regression test that:
  - Creates two fresh git repos.
  - Uses identical MCP handlers (no tool reconfiguration between repos).
  - Runs `engram_project_current` before init (expects actionable uninitialized response).
  - Runs `engram_project_init` in each repo.
  - Runs `engram_project_current` + `engram_project_diagnostics` after init (expects ready/healthy).
- Add a guard assertion in that flow by monkeypatching key CLI entrypoints (if imported) to raise, proving MCP path remains service-driven and CLI-independent for normal init/status.

2. `tests/test_services_project.py` (only if needed after step 1)
- Add a focused service-level cross-workspace status regression if MCP test alone does not adequately prove workspace switching semantics.

## Validation
- Run targeted tests first:
  - `pytest tests/test_mcp_tools.py -k "project_init or project_current or diagnostics or workspace"`
- Then run full impacted set:
  - `pytest tests/test_mcp_tools.py tests/test_services_project.py tests/test_mcp_server.py`

## Out of Scope
- No lifecycle/verification-gate changes (later phases).
- No workflow output contract changes (later phases).
- No CLI feature additions.
