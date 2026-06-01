# Implementation Plan: Add batch task payload validation service (30d66252)

## Scope
Add a batch task creation service entry point that accepts multiple create-task payloads, applies the same normalization and executable-metadata validation as single-task creation, and reports per-entry validation failures before any writes occur.

## Files
- src/engram/services/task/crud.py
- src/engram/services/task/__init__.py
- src/engram/services/task/validation.py
- tests/test_services_task.py

## Steps
1. Inspect current single-task creation path in `crud.py` and validation helpers in `validation.py`.
2. Add a new batch service function (service layer only) that:
   - accepts a list of task-create payloads,
   - normalizes each payload using existing normalization logic,
   - validates each payload using current executable-metadata rules,
   - accumulates per-entry errors with stable index mapping,
   - aborts before writes if any entry fails validation.
3. If all entries validate, delegate to existing task creation write path for each payload.
4. Export the new batch function in `src/engram/services/task/__init__.py`.
5. Add focused tests in `tests/test_services_task.py` covering:
   - all-valid batch creates expected tasks,
   - mixed-invalid batch returns per-entry errors and creates nothing,
   - validation behavior parity with single-task path for core required fields.
6. Run required verification command:
   - `uv run pytest tests/test_services_task.py -q -k create_m`
7. Run `engram_workflow_verify`; if blocked/failing, fix and rerun until pass.
8. Record task memory review outcome (`no_change` unless durable memory is produced).
9. Run `engram_workflow_finish` and stop.

## Risks / Checks
- Preserve current single-create behavior unchanged.
- Keep service module adapter-safe (no CLI/MCP imports).
- Ensure no partial writes happen on validation failure.
