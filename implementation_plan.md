# Implementation Plan - Task 0b622c80 (Phase 6.1)

## Scope
Refine `engram_workflow_start` startup-context coverage so the Work Order gives high-signal implementation context (objective, acceptance, relevant-file guidance, compact phase/task context) without broad repository scanning. Preserve current task selection and branch checkout behavior.

## Constraints and Boundaries
- Do not introduce Phase 7+ behaviors: no readiness lifecycle gates, `engram_workflow_verify`, finish gating, or memory-review enforcement.
- Keep output compact and non-duplicative.
- Respect service-layer boundaries (`src/engram/services` remains adapter-safe).
- No edits inside `planning/`, `workflow/`, or `.github/`.

## Current Investigation Plan
1. Inspect current startup output assembly and section composition:
- `src/engram/services/workflow_service.py`
- `src/engram/context/startup/orchestrator.py`
- `src/engram/context/startup/builders.py`
- `src/engram/context/startup/next_action.py`

2. Inspect tests that lock task selection/branch semantics and startup rendering:
- `tests/test_context.py`
- Related workflow-start tests found via targeted search.

3. Identify coverage gaps in startup guidance when task metadata is sparse:
- Missing/weak relevant-file hints
- Missing fallback search guidance
- Repetition across objective/acceptance/context blocks

## Planned Implementation
1. Add/adjust startup-context builders to improve high-signal guidance under sparse metadata, prioritizing:
- Clear objective + acceptance exposure
- Relevant files first; deterministic fallback search hints only when needed
- Compact guardrail/memory context with truncation metadata preserved

2. Keep orchestration responsibilities clear:
- Ensure orchestration composes existing context pieces without duplicating sections.
- Avoid behavior changes to task selection, branch switching, or resume mechanics.

3. Update/extend tests:
- Assert compact output contract and non-duplicative section behavior.
- Assert sparse metadata fallback guidance is present and stable.
- Confirm task-selection/branch-checkout behavior remains unchanged.

## Validation Plan
- Run targeted tests for context/workflow-start behavior first.
- Run broader unit tests impacted by touched modules.
- Confirm no new Phase 7+ semantics appear in output or logic.

## Out of Scope
- Any readiness lifecycle policy changes.
- `engram_workflow_verify` implementation.
- Finish-time verification or memory-review enforcement.
- Unrelated repository cleanup.
