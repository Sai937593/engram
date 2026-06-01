# Implementation Plan - Phase 6.2

## Scope
Update agent-facing guidance so memory review is phase-level follow-up, not a per-task finish requirement.

## Files
- docs/CODEX_HANDOFF_WORKFLOW_MVP_SIMPLIFICATION.md
- docs/USER_MANUAL.md
- src/engram/USER_MANUAL.md
- docs/skills/memory-review.md
- src/engram/mcp/tools/task_tools.py

## Planned changes
1. Remove or reword any statements that require `memory_review_outcome` before task finish.
2. Align workflow docs to use simplified flow: `start -> implement -> verify -> finish and commit`.
3. Reframe memory review guidance as phase-completion work using existing memory CRUD tools.
4. Update any finish/next-step messaging that still tells agents to log lessons or set `memory_review_outcome` before finish.
5. Keep all changes documentation/tool-message scoped; no workflow behavior redesign beyond wording alignment.

## Verification
- Run targeted checks:
  - `uv run pytest tests/ -m "not slow" -x --tb=short -q`
- Run workflow gate:
  - `engram_workflow_verify`

## Risks
- Potential mismatch between docs and transitional alias behavior (`engram_workflow_finish` vs `engram_workflow_finish_and_commit`).
- Missing one residual memory-review phrase in long docs.

## Done criteria
- All listed files no longer require per-task memory review before finish.
- Remaining memory-review instructions are explicitly phase-level.
- Workflow finish messaging is consistent with simplified flow.
