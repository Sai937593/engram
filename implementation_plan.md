# Implementation Plan - Task 3cfdbf33 (Phase 7.3)

## Scope
Expose `engram_workflow_verify` through the MCP workflow tool surface and return concise Markdown output using the shared workflow formatter. Keep behavior repo-local and branch-aware via existing service plumbing.

## Constraints and Boundaries
- One-task session only: execute only task `3cfdbf33`.
- Phase boundary: do not add finish gating, stale-verification enforcement, task auto-progression, or memory-review gates.
- Output boundary: keep verification responses compact; avoid dumping long raw logs.
- No-touch directories: `planning/`, `workflow/`, `.github/`.
- Service safety: `src/engram/services` must remain adapter-safe (no Click/Rich/CLI/subprocess/MCP adapter imports).
- Preserve existing `engram_workflow_start` / `engram_workflow_finish` contracts.

## Investigation Plan
1. Inspect current verify service result contract and formatter helpers:
- `src/engram/services/workflow_formatter.py`
- verify-related service functions already used by workflow tools.

2. Inspect MCP workflow tool registration and server wiring:
- `src/engram/mcp/tools/workflow_tools.py`
- `src/engram/mcp/server.py` (registration/bootstrap regression checks).

3. Inspect tests covering MCP tool registration and response behavior:
- `tests/test_mcp_tools.py`
- `tests/test_mcp_server.py`

## Planned Changes
1. Formatter:
- Ensure formatter exposes a compact verification Markdown shape with:
  - explicit pass/fail status
  - concise details block
  - exactly one next action line
- Fix any encoding/formatting artifacts in task display lines.

2. MCP workflow tools:
- Register a new async MCP tool `engram_workflow_verify` in workflow tools.
- Resolve bound project and primary repo path consistently with existing workflow tools.
- Delegate execution to existing verify workflow/service function (no duplicate business logic).
- Map unbound/misconfigured workspace errors through existing actionable error response path.

3. MCP server / exports:
- Ensure the new workflow tool is included via existing tool registration surfaces without regressing startup behavior.

4. Tests:
- Add/update tests to verify:
  - tool registration includes `engram_workflow_verify`
  - happy path returns compact Markdown with status and one next action
  - error paths remain actionable for missing repo bindings/config
  - existing start/finish tests remain green

## Validation Plan
- Run targeted tests first:
- `pytest tests/test_mcp_tools.py -k workflow_verify`
- `pytest tests/test_mcp_server.py`
- Then run full touched module if needed:
- `pytest tests/test_mcp_tools.py`

## Out of Scope
- Any finish blocking based on verify state.
- Automatic next-task selection/progression changes.
- Broad diagnostic/reporting refactors outside workflow verify output contract.
