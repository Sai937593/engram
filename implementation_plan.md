# Implementation Plan - Task 21b5e71e (Phase 9.4)

## Scope
Gate `engram_workflow_finish` on `memory_review_outcome` for the active task. If missing, finish must block with a compact next action. On successful finish, output must include the recorded memory review outcome and must not include auto-start guidance.

## Constraints and Boundaries
- One-task session only: execute only task `21b5e71e`.
- Keep changes limited to finish gating and finish output formatting.
- Preserve service/adapter boundaries (no CLI/MCP imports in `src/engram/services`).
- No-touch directories: `planning/`, `workflow/`, `.github/`.

## Investigation Plan
1. Review finish eligibility and finish flow in:
- `src/engram/services/workflow_service.py`

2. Review finish blocked/success formatting contracts in:
- `src/engram/services/workflow_formatter.py`

3. Review MCP finish tool error handling and output composition in:
- `src/engram/mcp/tools/workflow_tools.py`

4. Inspect tests covering finish gating/formatting and identify minimal updates.

## Planned Changes
1. Add/adjust service-level finish eligibility check to require non-null valid `memory_review_outcome` before any git side effects.

2. Ensure missing `memory_review_outcome` returns a deterministic blocked reason that MCP/tool formatter can map to a compact `## Next action` instructing the user/agent to record memory review outcome first.

3. Update finish success formatter path so the final success output includes the recorded memory review outcome explicitly.

4. Preserve existing compact finish style and no auto-start guidance.

5. Add/update focused tests for:
- finish blocked when memory review outcome is missing
- finish success includes memory review outcome
- no regressions in existing verification-gate behavior

## Validation Plan
- Run targeted unit tests for workflow service/formatter/tool modules.
- Run a broader relevant test slice if targeted tests indicate cross-module impact.
- Ensure zero failing tests before invoking `engram_workflow_finish`.

## Out of Scope
- Changing memory review taxonomy or allowed enum values.
- New phase automation behavior.
- Unrelated workflow output refactors.
