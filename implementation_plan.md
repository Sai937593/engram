# Implementation Plan - Phase 11.1 (a882f522)

## Scope
Add focused automated coverage for strict single-task creation and transactional batch creation behavior in:
- `tests/test_services_task.py`
- `tests/test_mcp_tools.py`

No production code changes unless a test exposes a contract gap that cannot be covered via tests alone.

## Target Behaviors
1. Single-task create success contract
- Verify valid MVP payload creates task with:
  - `status == "open"` (default)
  - `is_verified is False` (default)

2. Missing required fields contract
- Verify missing required executable metadata fails with actionable validation details.
- Verify failure performs zero writes (no partial task row inserted).

3. Weak/invalid payload diagnostics
- Verify weak metadata returns `TASK_METADATA_INCOMPLETE` with structured details (`missing_fields`, `weak_fields`, reasons).
- Verify invalid enum fields (status/priority) return stable, actionable validation errors.

4. Batch create all-or-nothing contract
- Success path: `create_many_tasks` writes all entries when all are valid.
- Failure path: when any entry is invalid, write none and return per-entry failure index/details.

5. MCP batch tool wiring
- `engram_task_create_many` success: compact success payload with created task ids/titles.
- `engram_task_create_many` failure: compact error payload surfaces invalid entry index/details from service layer.

## File-by-File Plan
- `tests/test_services_task.py`
  - Add/adjust narrowly scoped tests for strict creation and create-many atomic behavior.
  - Ensure assertions explicitly check row counts before/after failure cases.

- `tests/test_mcp_tools.py`
  - Add/adjust MCP handler tests for `engram_task_create_many` success/failure payloads.
  - Keep assertions deterministic and compact.

## Verification
- Run targeted tests first:
  - `uv run pytest tests/test_services_task.py -k "create_task or create_many"`
  - `uv run pytest tests/test_mcp_tools.py -k "task_create_many"`
- Run full required workflow verification using `engram_workflow_verify`.
- If green, run `engram_workflow_finish_and_commit` and stop.
