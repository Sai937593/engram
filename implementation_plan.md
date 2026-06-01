# Implementation Plan: Replace verify command plan with MVP target checks (8b3bd43b)

## Scope
Update verify command resolution in the workflow verify service to the Phase 4 command contract and add targeted tests for exact order/content, without changing unrelated verify behavior.

## Files to update
- src/engram/services/workflow_verify_service.py
- tests/test_services_workflow_verify.py

## Planned changes
1. Replace `VERIFY_COMMANDS` with the exact Phase 4 base commands in this order:
   - `ruff format .`
   - `ruff check . --fix`
   - `python -m engram.hooks.py_structure`
   - `pytest tests/ -m "not slow" -x --tb=short -q`

2. Keep `_resolve_verify_commands` explicit and ordered:
   - If `uv.lock` exists, prefix each base command with `uv run`.
   - Otherwise, keep the existing Python-module fallback structure.

3. Update/extend service tests to lock the command contract:
   - Assert pass-path execution runs all commands in exact order.
   - Assert persisted pass details reflect the new command set.
   - Add focused assertions for command resolution behavior.

## Verification
Run:
- `uv run pytest tests/test_services_workflow_verify.py -q`

## Notes
- Stay in scope: no staging, no `is_verified` mutation, no MCP formatter changes.
- No edits under `planning/`, `workflow/`, or `.github/`.
