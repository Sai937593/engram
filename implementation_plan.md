# Implementation Plan - Task 9770c73a

## Scope
Restore parity between `docs/USER_MANUAL.md` and `src/engram/USER_MANUAL.md` by syncing the Phase 10 Task Decomposition Skill discoverability guidance in the session startup section.

## Constraints and Boundaries
- One-task session only: execute only task `9770c73a`.
- Keep changes limited to the two USER_MANUAL files unless verification requires a minimal in-scope fix.
- Preserve no-touch directories: `planning/`, `workflow/`, `.github/`.

## Inputs to Use
- `docs/USER_MANUAL.md`
- `src/engram/USER_MANUAL.md`

## Planned Changes
1. Compare the session startup sections in both manuals.
2. Copy missing Phase 10 task decomposition discoverability guidance into the packaged manual copy (`src/engram/USER_MANUAL.md`) or align wording so both are equivalent.
3. Recheck both manuals for textual parity in that section.
4. Record a concise task evidence note summarizing what was synced.

## Validation Plan
- Confirm both manuals contain matching guidance for task decomposition discoverability in session startup.
- Run `uv run pytest tests -q`.
- Run `engram_workflow_verify`; if it fails, fix the first actionable issue and rerun.

## Out of Scope
- Any additional feature or workflow change outside this doc parity fix.
- Work on any task other than `9770c73a` in this session.
