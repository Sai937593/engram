# Implementation Plan - Update finish formatting and workflow-facing docs (Task 1eefdbb1)

## Scope
Update workflow formatter strings and nearest workflow-facing docs so guidance consistently prefers `engram_workflow_finish_and_commit`, states that verify stages changes, and states that finish-and-commit only commits/pushes already-staged work. Keep existing memory-review gate guidance intact.

## Planned Changes
1. Update workflow formatter text in `src/engram/services/workflow_formatter.py`
- Replace finish references that currently point to `engram_workflow_finish` with `engram_workflow_finish_and_commit` as the primary action.
- Keep transitional wording if needed, but make the old name clearly secondary.
- Preserve memory-review gate language and outcomes.

2. Confirm verify success guidance in `src/engram/mcp/tools/workflow_tools.py`
- Ensure verify success next-action text points to `engram_workflow_finish_and_commit`.
- Do not change verify behavior or staging semantics.

3. Update workflow-facing docs only (no broad cleanup)
- `src/engram/USER_MANUAL.md`
- `docs/CODEX_HANDOFF_WORKFLOW_MVP_SIMPLIFICATION.md`
- `docs/CODEX_IMPLEMENTATION_PHASES_WORKFLOW_MVP_SIMPLIFICATION.md`
- Remove/adjust nearby statements that imply finish performs staging or reruns validation.
- Keep mentions of `engram_workflow_finish` only as deprecated/transitional where necessary.

4. Keep changes tightly scoped
- No edits outside task-relevant workflow text and examples.
- No behavior changes beyond wording alignment.

## Verification
- Run required task verification command:
  - `uv run pytest tests/test_mcp_tools.py tests/test_workflow_redesign_phase_15_end_to_end.py -q`
- Run `engram_workflow_verify` and address any failures.

## Out Of Scope
- Full historical doc cleanup across the repository.
- Workflow design changes beyond this wording alignment.
- Removing the memory-review gate before Phase 6.