# Implementation Plan - Phase 12.2 (Task 243bdd98)

## Scope
Enforce richer task-quality validation when promoting tasks to `ready`, reusing the Phase 12.1 validation contract and preserving deterministic error payloads.

## Files in scope
- src/engram/services/task/validation.py
- src/engram/services/task/update_resolution.py
- src/engram/mcp/tools/helpers.py
- tests/test_services_task.py

## Plan
1. Confirm the ready-promotion gate in service update resolution always uses the Phase 12.1 evaluator outputs (`missing_fields`, `weak_fields`, `weak_field_reasons`, `evaluated_fields`) without ad hoc checks.
2. Ensure update flows that transition into `ready` from non-ready statuses consistently call the same validation function with effective field values.
3. If needed, align MCP error guidance for `READY_METADATA_INCOMPLETE` with richer quality failures (weak vs missing metadata) while keeping compatibility.
4. Add/adjust focused tests for:
   - rejection on weak metadata with field-specific reasons,
   - rejection on missing metadata,
   - success path for valid metadata,
   - stability of response payload shape.
5. Run focused task-service tests for ready promotion, then run full `pytest`.

## Non-goals
- No changes outside Task 243bdd98 scope.
- No workflow/planning/.github edits.
- No unrelated refactors.
