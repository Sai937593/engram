# Implementation Plan: Atomic create-many task service (8d29fab0)

## Scope
Implement all-or-nothing persistence for `create_many_tasks` after preflight validation succeeds, while preserving existing single-task defaults, dependency normalization behavior, and response shape.

## Proposed changes
1. Add a task-model batch insert path:
- Introduce a new `Task.create_many(project_id: str, payloads: list[dict[str, object]]) -> list[Task]` method in `src/engram/models/task/model.py`.
- Perform all inserts in a single DB transaction (`BEGIN` + commit/rollback semantics via one shared connection).
- Reuse existing field serialization/default behavior equivalent to `Task.create` (id generation, objective->description compatibility, tags/relevant_files/search_hints serialization, status/priority passthrough).
- On any insert failure, rollback and re-raise so zero rows persist.

2. Switch service batch create to atomic model API:
- Update `create_many_tasks` in `src/engram/services/task/crud.py` to:
  - Keep current full preflight validation and per-index error aggregation behavior unchanged.
  - After successful preflight, call `Task.create_many(...)` once.
  - Return `_task_to_dict(...)` for each created task in stable input order.

3. Focused tests for atomicity and behavior preservation:
- Extend `tests/test_services_task.py` with tests that verify:
  - Successful valid batch still creates all tasks and preserves normalization/defaults.
  - If persistence fails mid-batch (simulated via monkeypatching DB execute), no new task rows are persisted.
  - Existing validation-failure path still writes zero rows and returns `TASK_BATCH_VALIDATION_FAILED` details.

## Verification
- Run focused tests first:
  - `uv run pytest tests/test_services_task.py -k create_many_tasks`
- Then run full workflow verification via MCP:
  - `engram_workflow_verify`

## Risks and mitigations
- Risk: Divergence between `Task.create` and `Task.create_many` defaults/serialization.
- Mitigation: Keep field handling logic structurally aligned and cover with regression assertions in create-many tests.
