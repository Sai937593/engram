# Implementation Plan - Task cc2040e7

## Scope
Remove mandatory Git-hook language from active workflow guidance so normal task execution is clearly based on `engram_workflow_verify`, while keeping CI described as an independent check.

## Files in scope
- `agent-files/skills/engram-start-task-template.md`
- `README.md`
- `docs/USER_MANUAL.md`
- `docs/CODEX_HANDOFF_WORKFLOW_MVP_SIMPLIFICATION.md` (historical check only; edit only if active wording is ambiguous)

## Planned edits
1. Update the start-task template text that currently describes verify as running "hook scripts" so it instead describes repo-local quality checks (format, lint, tests) without requiring Git hooks.
2. Sweep `README.md` and `docs/USER_MANUAL.md` for active workflow wording that implies pre-commit/pre-push is required; replace with wording that:
   - defines `engram_workflow_verify` as the local quality gate, and
   - keeps hook configs optional developer convenience.
3. Leave historical implementation docs as historical unless a line reads as active instruction; if needed, add concise clarifying language rather than broad rewrites.

## Verification
1. Run targeted grep checks for hook-dependent wording in active docs.
2. Run `engram_workflow_verify` to execute required local checks and auto-stage changes on success.
3. If verification passes, run `engram_workflow_finish_and_commit` to complete the task.

## Deliverable
Active docs and templates no longer require Git hooks for normal Engram task execution, and verification/finish workflow remains aligned with MVP behavior.
