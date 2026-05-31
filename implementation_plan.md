# Implementation Plan - Task 52ac8ebf

## Scope
Add explicit `draft` and `ready` task statuses across schema, model, validation, and service/MCP-facing task surfaces while preserving existing lifecycle behavior.

## Constraints and Boundaries
- One-task session only: execute only task `52ac8ebf`.
- No edits in `planning/`, `workflow/`, or `.github/`.
- Keep service layers adapter-safe (no CLI/MCP adapter imports in services).
- Keep Phase 11 gate minimal: only metadata/status gating needed for `draft` vs `ready`.

## Inputs to Use
- `src/engram/db/schema.py`
- `src/engram/db/migrations.py`
- `src/engram/models/task/model.py`
- `src/engram/services/task/validation.py`
- `src/engram/services/task/crud.py`
- Related task list/next or workflow-start selection files surfaced during implementation.
- Target tests: `tests/test_task.py`, `tests/test_services_task.py`, `tests/test_mcp_tools.py`.

## Planned Changes
1. Expand canonical task status enum/constants to include `draft` and `ready` where task statuses are defined/validated.
2. Update schema/migration/model defaults and constraints so persistence accepts the expanded status set without breaking existing states.
3. Update service-layer validation and CRUD/task selection logic so:
   - `ready` is actionable for next/start selection.
   - `draft` is non-actionable until promoted.
   - `in-progress` resume behavior remains intact.
4. Update user-visible lifecycle/status documentation where status sets are explicitly listed.
5. Add/adjust targeted tests for status acceptance and selection behavior.

## Validation Plan
- Run: `uv run pytest tests/test_task.py -q tests/test_services_task.py -q tests/test_mcp_tools.py -q`
- Run: `engram_workflow_verify`
- If verification fails, fix the first actionable issue and rerun verification.

## Out of Scope
- Any Phase 12 quality heuristics or richer readiness scoring.
- Any work on tasks other than `52ac8ebf` in this session.
