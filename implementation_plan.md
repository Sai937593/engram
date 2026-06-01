## Implementation Plan - Task c2b08d27

### Scope
- Update phase-review guidance in:
  - `docs/CODEX_HANDOFF_WORKFLOW_MVP_SIMPLIFICATION.md`
  - `docs/USER_MANUAL.md`
  - `src/engram/USER_MANUAL.md`
- Keep `AGENTS.md` unchanged unless a stable repo-wide rule is required.

### Planned Changes
1. Align all three docs to describe phase review as phase-level memory curation using existing memory tools.
2. Ensure phase completion flow explicitly points to `engram_phase_complete` after memory review and cleanup.
3. Remove or correct contradictory guidance about:
   - raw SQLite access by agents,
   - dedicated/special phase memory-review start tools.
4. Sync tool lists so memory batch helpers are consistently documented where phase review instructions appear.

### Verification
1. Run the task-provided grep check:
   - `rg -n "phase review|memory review|engram_phase_complete|engram_memory_(list|get|create|update|delete|update_many|delete_many)|special phase memory review|raw SQLite" docs/CODEX_HANDOFF_WORKFLOW_MVP_SIMPLIFICATION.md docs/USER_MANUAL.md src/engram/USER_MANUAL.md AGENTS.md`
2. Run `engram_workflow_verify`.
3. If verify passes, run `engram_workflow_finish_and_commit`.

