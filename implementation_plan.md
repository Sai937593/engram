# Implementation Plan - Phase 9.1 (c7de0990)

## Scope
Align phase-review and memory-review guidance with Workflow MVP simplification:
- Keep phase review on normal phase/task/memory tools.
- Reinforce memory curation at phase level, not per-task finish gates.
- Explicitly prohibit raw SQLite/ad hoc DB scripts and special phase memory-review start tools.
- Preserve guidance that root `AGENTS.md` is updated only for stable repository-wide rules.

## Planned Changes
1. Update `agent-files/skills/engram-phase-review-template.md`:
- Confirm tool list only includes normal phase/task/memory tools.
- Keep explicit prohibition on raw SQLite/ad hoc DB scripts.
- Ensure wording clearly states phase-level memory review and no special phase memory-review start tool.
- Keep/clarify `AGENTS.md` update rule as stable repository-wide only.

2. Update `docs/skills/memory-review.md`:
- Reframe as phase-level curation guidance for durable knowledge.
- Explicitly state this is not a per-task finish gate.
- Add explicit prohibition on raw SQLite access and direct `.engram/memory.db` inspection/mutation.
- Reference normal memory CRUD and phase completion tools only.
- Remove wording that implies special phase memory-review start behavior.

## Verification
1. Run:
`rg -n "engram_phase_complete|engram_memory_(list|get|create|update|delete|update_many|delete_many)|raw SQLite|special phase memory review|AGENTS.md" agent-files/skills/engram-phase-review-template.md docs/skills/memory-review.md`
2. Run `mcp__engram.engram_workflow_verify`.
3. If verify passes, run `mcp__engram.engram_workflow_finish_and_commit`.

## Out of Scope
- Any workflow/service code changes.
- Changes outside the two target documentation files.
