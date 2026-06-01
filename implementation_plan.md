# Implementation Plan: Register batch task creation MCP tool (28c8a290)

## Scope
Add `engram_task_create_many` as a thin MCP adapter over the existing atomic service entry point, preserving compact MCP success/error response conventions and returning exact per-entry validation failures without partial writes.

## Proposed changes
1. Add tool handler in `src/engram/mcp/tools/task_tools.py`:
- Register `engram_task_create_many(tasks: list[dict[str, Any]]) -> str` under `register_task_tools`.
- Resolve current project once and delegate to the existing service-layer batch API (`create_many_tasks` through `engram.mcp.tools` exports).
- On success, return compact YAML via `_respond` with `ok: true` and created task refs (IDs/titles) for the full batch.
- On `EngramServiceError`, return `_respond_error` unchanged so `TASK_BATCH_VALIDATION_FAILED` details remain exact and per-entry.

2. Ensure module exports support the new adapter path:
- Update `src/engram/mcp/tools/__init__.py` only if needed so `create_many_tasks` is available through `engram.mcp.tools` like other task service delegates.
- Keep the change minimal and consistent with existing import/export patterns.

3. Add focused MCP tests in `tests/test_mcp_tools.py`:
- Registration test asserts `engram_task_create_many` is present in `register_tools`.
- Happy-path test validates compact success response and that all requested tasks are created.
- Validation-failure test asserts error code/details include per-index failures and confirms zero tasks persisted for the batch.

## Verification
1. `uv run pytest tests/test_mcp_tools.py -q -k task_create_many`
2. `engram_workflow_verify`

## Risks and mitigations
- Risk: Response shape drifts from existing MCP write-tool compactness.
- Mitigation: Match current `_respond`/`_respond_error` patterns and assert shape directly in MCP tests.
