# Implementation Plan - Task eb75ad51

## Scope
Run a final repo-wide documentation audit for phase-review regressions and resolve any remaining active guidance that conflicts with the simplified workflow.

## Findings from initial audit
- `AGENTS.md` and `agent-files/root-agents-template.md` contain valid guardrails forbidding raw SQLite / direct `.engram/memory.db` inspection.
- `docs/skills/memory-review.md` and `agent-files/skills/engram-phase-review-template.md` correctly require normal memory CRUD tools and explicitly forbid any special phase-memory-review start tool.
- Matches in `docs/CODEX_IMPLEMENTATION_PHASES_WORKFLOW_MVP_SIMPLIFICATION.md` and `docs/CODEX_HANDOFF_WORKFLOW_MVP_SIMPLIFICATION.md` are historical planning/handoff context, not active operational guidance.
- `docs/USER_MANUAL.md` references `.engram/memory.db` as product architecture/storage, not as an instruction for agents to query it directly.

## Planned edits
1. Perform one more targeted scan for nearby wording variants (e.g., `phase_memory_review_start`, `memory review gate`, `draft/ready/todo` references tied to task finish) across `docs/`, `agent-files/`, and root `AGENTS.md`.
2. If any active contradictory wording exists, apply minimal text edits to align with:
   - phase-level memory review only,
   - no special phase-review startup tool,
   - no direct raw SQLite guidance for agent operations.
3. Preserve historical docs as historical; avoid rewriting implementation history unless needed for clarity labels.

## Verification
- Run the required task grep:
  - `rg -n "raw SQLite|memory\.db|special phase memory review|phase memory review start|per-task memory review" docs agent-files AGENTS.md`
- Run one supplemental grep for adjacent legacy phrasing to confirm no active regressions remain.
- Then run `engram_workflow_verify` as required workflow verification before finish.

## Deliverable
A concise repo-audit outcome with any minimal doc fixes needed, verified via workflow checks.