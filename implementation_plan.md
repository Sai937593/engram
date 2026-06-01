# Implementation Plan - Phase 8.1 Batch Memory Update Service

## Scope
Implement a transactional, project-scoped `update_many` path for memory updates in service/support layers, reusing existing single-memory validation and preserving all-or-nothing semantics.

## Planned Changes
1. Add batch update validation/resolution helper(s) in `src/engram/services/memory_update_support.py`:
- Require a non-empty list of update entries.
- Validate each entry shape includes `memory_ref` and at least one update field.
- Reject duplicate memory references within the same batch.
- Resolve all memory references through project scoping (`get_project_memory`) before applying updates.
- Reuse `validate_memory_updates` for per-entry field/type/scope validation.
- Return fully validated `(memory_item, resolved_updates)` units for apply phase.

2. Add service API in `src/engram/services/memory_service.py`:
- New `update_memories(project_id: str, entries: list[dict[str, JsonValue]]) -> dict[str, JsonValue]` (name may be adjusted to match existing service naming).
- Perform full prevalidation first; do not mutate during validation.
- Apply updates in a single DB transaction (`BEGIN`/`COMMIT`, rollback on any exception).
- Normalize model `ValueError` into `ValidationError` with clear batch context.
- Return concise success payload with `updated_count` and `updated_ids` (or compact summaries if already established pattern exists).

3. Error contract alignment:
- Reuse existing error codes where practical (`INVALID_MEMORY_UPDATE`, `INVALID_MEMORY_UPDATE_FIELD`, `MEMORY_NOT_FOUND`, etc.).
- Add specific batch-level codes only if needed for clarity (e.g., empty batch, duplicate refs), defined consistently in service-layer error usage.

4. Tests in `tests/test_services_memory.py`:
- Success path updates multiple rows in one request and returns expected summary.
- Reject empty batch.
- Reject duplicate refs.
- Reject unknown fields.
- Reject unknown/cross-project ref.
- Reject invalid payload values (e.g., invalid type/scope/level transition).
- Atomicity test: mixed valid+invalid entry causes no row updates.
- Verify single-memory `update_memory` behavior unchanged.

## Validation Steps
1. Run targeted tests first:
- `uv run pytest tests/test_services_memory.py -k update`
2. Run full memory service tests:
- `uv run pytest tests/test_services_memory.py`
3. Run workflow verification gate:
- `engram_workflow_verify`
4. Finish and commit via workflow tool after successful verification:
- `engram_workflow_finish_and_commit`
