# Implementation Plan - Task 1851de97 (Phase 6.2)

## Scope
Curate Work Order guardrails and task-memory signals so `engram_workflow_start` stays compact, deterministic, and useful for implementation startup. Improve ordering/caps/truncation and sparse-memory guidance without introducing retrieval-system overhauls or new memory-mutation surfaces.

## Constraints and Boundaries
- Do not introduce Phase 7+ behaviors: no readiness lifecycle gates, `engram_workflow_verify`, finish gating, or memory-review enforcement.
- Keep output compact and non-duplicative.
- Respect service-layer boundaries (`src/engram/services` remains adapter-safe).
- No edits inside `planning/`, `workflow/`, or `.github/`.
- Exclude semantic retrieval overhauls, raw DB access, and new memory-mutation APIs.

## Current Investigation Plan
1. Inspect current startup output assembly and section composition:
- `src/engram/context/startup/builders.py`
- `src/engram/context/startup/options.py`
- `src/engram/memory_retrieval/startup_orchestration.py`
- `src/engram/services/workflow_formatter.py`

2. Inspect tests that lock startup rendering and memory/guardrail behavior:
- `tests/test_context.py`
- Related workflow-start tests discovered via targeted search.

3. Identify coverage gaps against acceptance criteria:
- Guardrails/task-memory separation clarity
- Deterministic ordering and compact caps
- Truncation metadata visibility and stability
- Useful sparse-memory next-step guidance

## Planned Implementation
1. Add/adjust startup-context builders and formatter behavior to ensure:
- Guardrails and task-memory are clearly separated and deterministic
- Section output remains compact under configured budgets
- Truncation behavior and indicators remain explicit and stable

2. Refine startup memory orchestration behavior for sparse/weak candidates:
- Improve empty/sparse task-memory guidance with concrete next-step search hints
- Avoid filler content while preserving current retrieval contracts

3. Update/extend tests:
- Assert deterministic ordering and clear section separation
- Assert sparse-memory guidance behavior
- Assert output budgets/truncation behavior remains enforced
- Keep service/MCP adapter boundaries unaffected

## Validation Plan
- Run targeted tests for startup context/workflow formatter behavior first.
- Run broader unit tests impacted by touched modules.
- Confirm no semantic retrieval overhaul or adapter-boundary regressions.

## Out of Scope
- Any readiness lifecycle policy changes.
- `engram_workflow_verify` implementation.
- Finish-time verification or memory-review enforcement.
- Any raw DB access pathway additions.
- Any new memory-mutation or manual task-tracking surfaces.
- Unrelated repository cleanup.
