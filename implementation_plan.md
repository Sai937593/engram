# Implementation Plan - Task b884eb2c

## Scope
Define and implement the Phase 12.1 service-layer task-quality validation contract for ready promotion, expanding from missing-field checks to deterministic weak-metadata heuristics and a stable error payload shape consumable by services/MCP.

## Constraints and Boundaries
- One-task session only: execute only task `b884eb2c`.
- No edits in `planning/`, `workflow/`, or `.github/`.
- Keep contract metadata-focused only; do not introduce lifecycle behavior beyond validation.
- Preserve CLI/service boundary: implementation stays in services and tests.

## Inputs to Use
- `src/engram/services/task/validation.py`
- `src/engram/services/task/update_resolution.py`
- `tests/test_services_task.py`
- `docs/CODEX_IMPLEMENTATION_PHASES_WORKFLOW_REDESIGN.md`

## Planned Changes
1. Review current ready-metadata validation contract and identify extension points for weak-field detection.
2. Define deterministic weak-field heuristics for evaluated metadata fields (description, acceptance, relevant files, and any additional task metadata currently gated by ready promotion).
3. Implement a stable validation result/payload shape that distinguishes missing fields from weak fields without coupling to CLI formatting.
4. Wire the richer validation contract through task update/promotion resolution paths used by services and MCP.
5. Add focused unit tests in `tests/test_services_task.py` covering pass/fail permutations, deterministic weak-field outcomes, and payload stability.

## Validation Plan
- Run focused module tests: `uv run pytest tests/test_services_task.py -q`
- Run workflow verification gate: `engram_workflow_verify`
- If verification fails, fix the first actionable issue and rerun.

## Out of Scope
- Workflow start/selection policy changes.
- Finish/verify gate behavior changes unrelated to task metadata validation.
- Any task other than `b884eb2c`.
