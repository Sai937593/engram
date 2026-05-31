# Implementation Plan - Task a656f75e

## Scope
Gate promotion from `draft` to `ready` on a minimum execution metadata contract, with actionable validation errors, while keeping Phase 11 minimal and deferring richer quality checks to Phase 12.

## Constraints and Boundaries
- One-task session only: execute only task `a656f75e`.
- No edits in `planning/`, `workflow/`, or `.github/`.
- Service layers must remain adapter-safe (no CLI/MCP adapter imports in services).
- Keep Phase 11 readiness gate minimal; do not add Phase 12 metadata-quality heuristics.

## Inputs to Use
- `src/engram/services/task/validation.py`
- `src/engram/services/task/crud.py`
- `src/engram/services/task/update_resolution.py`
- `src/engram/mcp/tools/task_tools.py`
- `tests/test_services_task.py`
- `tests/test_mcp_tools.py`

## Planned Changes
1. Define/extend minimal readiness validation in task validation services for transitions into `ready`.
2. Enforce the gate in task update flow so attempts to promote `draft -> ready` fail fast when required metadata is missing.
3. Ensure the returned error is actionable and names missing metadata fields.
4. Keep behavior narrow to promotion gating and avoid any deep scoring/quality logic.
5. Add/adjust tests to cover:
   - Successful promotion when minimum metadata exists.
   - Failure with clear missing-field feedback when metadata is incomplete.

## Validation Plan
- Run: `uv run pytest tests/test_services_task.py -q tests/test_mcp_tools.py -q`
- Run: `engram_workflow_verify`
- If verification fails, fix the first actionable issue and rerun verification.

## Out of Scope
- Phase 12 rich metadata quality checks/heuristics.
- Any work on tasks other than `a656f75e` in this session.
