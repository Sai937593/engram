# Implementation Plan - Task 85f39048

## Scope
Implement phase lifecycle service transitions for `update`, `cancel`, and `archive` with deterministic validation and active-phase safety, keeping lifecycle logic centralized in service/model layers.

## Files
- src/engram/services/phase_service.py
- src/engram/models/phase.py
- src/engram/models/phase_persistence.py
- src/engram/models/phase_transitions.py
- tests/test_services_phase.py
- tests/test_phase.py

## Steps
1. Inspect current phase model/service write paths to identify where update/cancel/archive behavior is currently ad hoc or missing.
2. Add service-layer APIs for phase update, cancel, and archive operations that:
   - resolve phase references deterministically,
   - validate invalid references and duplicate titles,
   - enforce unfinished-task safety for blocked transitions,
   - preserve active-phase coherence when cancel/archive touch active phases.
3. Implement or extend model/persistence transition helpers used by the service APIs, with adapter-safe boundaries.
4. Add/adjust tests covering:
   - successful update/cancel/archive transitions,
   - duplicate/invalid reference failures,
   - unfinished-task blocking behavior,
   - active-phase coherence after lifecycle changes.
5. Run required verification command:
   - `uv run pytest tests/test_services_phase.py tests/test_phase.py -q`
6. If green, run `engram_workflow_verify`, record memory review outcome on the active task, then run `engram_workflow_finish`.

## Constraints Checklist
- Only this one Engram task in this session.
- No edits in `planning/`, `workflow/`, or `.github/`.
- Service layer remains CLI/MCP adapter-safe.
- Keep changes minimal and task-scoped.
