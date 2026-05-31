# Implementation Plan - Task 8e1172e6 (Phase 6.3)

## Scope
Add regression tests for `engram_workflow_start` Work Order output in dense and sparse startup states after Phase 6 refinements. Lock behavior for compact high-signal context, sparse-memory guidance, single `Next action` rendering, and deterministic output budget behavior across service and MCP-visible paths.

## Constraints and Boundaries
- One-task session only: execute only task `8e1172e6`.
- Test-focused scope: no new workflow lifecycle states, no finish gating, no verify-phase behavior.
- Keep edits within currently implemented workflow-start surface.
- Respect no-touch directories: `planning/`, `workflow/`, `.github/`.
- Preserve service/adapter boundaries in `src/engram/services`.

## Investigation Plan
1. Review existing startup and workflow-start regression tests:
- `tests/test_context.py`
- `tests/test_services_workflow_start_basic.py`
- `tests/test_mcp_tools.py`
- `tests/test_workflow_redesign_phase_5_regressions.py`

2. Map acceptance criteria to concrete assertions:
- Dense guardrail + memory rendering remains compact and deterministic.
- Sparse task metadata/memory path shows useful guidance without duplication.
- Exactly one `Next action` section is emitted.
- Budget/truncation behavior stays deterministic.

3. Identify whether any small fixture/helper additions are needed to avoid brittle assertions.

## Planned Changes
1. Add or refine tests for dense startup state:
- Verify compact Work Order sections with high-signal guardrail/memory content.
- Verify no duplicated obvious task metadata.

2. Add or refine tests for sparse startup state:
- Verify fallback guidance when relevant memories/files are absent.
- Verify output still includes one actionable `Next action`.

3. Add/adjust budget stability assertions:
- Lock deterministic truncation/ordering behavior under constrained output budgets.

4. If needed, make minimal production adjustments only to satisfy validated regression expectations and keep behavior consistent across service + MCP entry points.

## Validation Plan
- Run targeted tests for edited modules first.
- Run the full related workflow-start test set listed above.
- Ensure zero failures before any finish step.

## Out of Scope
- Implementing later-phase verification or readiness gates.
- Changing `engram_workflow_finish` behavior.
- Broad refactors outside startup Work Order regression coverage.
