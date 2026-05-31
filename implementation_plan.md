# Implementation Plan - Task c29f71bb (Phase 7.1)

## Scope
Add repo-local persistence for workflow verification results and expose a service contract to record and fetch the latest verification outcome for a task/workflow run. Keep this phase limited to storage, schema/migration, and lookup support for later freshness checks and concise summaries.

## Constraints and Boundaries
- One-task session only: execute only task `c29f71bb`.
- Phase boundary: do not add `engram_workflow_finish` blocking, stale-verification enforcement, or memory-review gating.
- Respect no-touch directories: `planning/`, `workflow/`, `.github/`.
- Preserve service/adapter boundaries in `src/engram/services`.
- Keep migrations idempotent and deterministic for fresh and legacy repos.

## Investigation Plan
1. Inspect current DB schema/migration patterns in:
- `src/engram/db/schema.py`
- `src/engram/db/migrations.py`

2. Inspect current workflow service surface in:
- `src/engram/services/workflow_service.py`

3. Inspect existing DB/service tests and fixtures in:
- `tests/test_db.py`
- Related workflow service tests if needed

4. Define minimal verification record fields required now for:
- Pass/fail outcome persistence
- Timestamped recency/freshness comparison inputs
- Basic user-facing summary support

## Planned Changes
1. Schema:
- Add a dedicated verification-state table (or equivalent repo-local structure) keyed for task/workflow association with deterministic timestamps and status fields.
- Add indexes/constraints needed for latest-outcome lookup and idempotent writes.

2. Migrations:
- Add migration/backfill logic that safely upgrades existing DBs.
- Ensure repeated init/migration runs remain no-op safe via table/column existence checks.

3. Service contract:
- Add workflow service helpers to:
- Record a verification result.
- Fetch the latest verification result for a task/workflow.
- Return structured data suitable for later freshness checks and concise summaries.

4. Tests:
- Add/extend DB migration tests for fresh + legacy initialization determinism.
- Add/extend service/DB tests validating record + latest lookup semantics and non-blocking behavior.

## Validation Plan
- Run targeted tests for touched files first.
- Run full relevant test modules for DB + workflow service paths.
- Ensure zero failures before any `engram_workflow_finish` call.

## Out of Scope
- Any finish-time gating or enforcement behavior.
- Memory-review policy enforcement.
- Unrelated task lifecycle or CLI UX changes.
