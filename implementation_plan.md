# Implementation Plan - Phase 11.5 (c1085f3c)

## Scope
Add compact regression coverage for the simplified phase-review contract:
- `workflow_finish` remains independent of per-task `memory_review_outcome`.
- Phase completion can be preceded by normal MCP memory CRUD operations, with no special phase-memory lifecycle tool.

## Findings from current state
- `tests/test_services_workflow_finish.py` already includes service-level regression tests confirming finish succeeds when `memory_review_outcome` is missing or arbitrary.
- Existing MCP tests validate memory CRUD tools and phase completion separately, but do not yet assert a single end-to-end MCP flow that performs memory CRUD before `engram_phase_complete`.

## Planned changes
1. Keep `tests/test_services_workflow_finish.py` focused and compact:
   - Verify existing finish-vs-memory-review tests still reflect current contract.
   - Only adjust if assertions are ambiguous or redundant.
2. Add one focused MCP regression test (in `tests/test_mcp_tools.py` or `tests/test_mcp_server.py`) that:
   - Creates/binds a project and active phase.
   - Uses normal memory CRUD tools (`engram_memory_create`, `engram_memory_update`, `engram_memory_delete` or equivalent compact sequence).
   - Completes all phase tasks and calls `engram_phase_complete` successfully.
   - Asserts no special phase-memory tool participation is required in that path.
3. Keep assertions narrow to MVP behavior and avoid historical workflow states.
4. Run task-scoped verification command:
   - `uv run pytest tests/test_services_workflow_finish.py tests/test_mcp_tools.py tests/test_mcp_server.py -q -k "memory_review_outcome or engram_phase_complete or memory_"`
5. Run `engram_workflow_verify`.
6. Run `engram_workflow_finish_and_commit`.

## Non-goals
- No changes to phase-review skill docs.
- No new dedicated phase-memory-review tool.
- No broad refactor of workflow/memory services.
