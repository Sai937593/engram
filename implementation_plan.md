# Phase 8.2 Implementation Plan: Transactional Batch Memory Delete Service

## Scope
Add a service-level batch delete path that prevalidates all requested memory IDs, rejects invalid batches with clear errors, and performs deletion only when the entire batch is valid. Preserve existing single-delete behavior.

## Planned Changes
1. Add batch delete validation/resolution helper in `src/engram/services/memory_update_support.py`.
- Validate non-empty ID list.
- Normalize IDs and reject empty IDs.
- Reject duplicate IDs.
- Resolve each ID with existing project-scoped lookup (`get_project_memory`) so missing/foreign IDs fail early.

2. Add transactional batch delete service function in `src/engram/services/memory_service.py`.
- New function (e.g. `delete_memories`) accepts `project_id` and list of memory IDs.
- Prevalidate via the new helper before any writes.
- Use a single DB transaction and delete all resolved IDs.
- Return concise result shape with count and deleted IDs.

3. Keep single-delete semantics unchanged.
- Do not alter existing lifecycle delete behavior.
- Keep batch delete scoped only to explicit deletion, not a generic mutation runner.

4. Add focused service tests in `tests/test_services_memory.py`.
- Success case deletes multiple valid IDs and returns `{deleted_count, deleted_ids}`.
- Empty batch failure.
- Duplicate IDs failure.
- Missing/foreign ID failure.
- Atomicity: if one ID is invalid, no deletion occurs.

## Verification
- Run `engram_workflow_verify`.
- If checks fail, fix only task-related failures and rerun.
- On success, run `engram_workflow_finish_and_commit`.
