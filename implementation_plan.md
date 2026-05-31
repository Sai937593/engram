# Implementation Plan - Task b26fc802 (Phase 3.3)

## Scope
Rewrite published manuals for repo-local, MCP-first workflow behavior without changing product code. Keep CLI documentation trimmed to optional human utilities (`init`, `guide`, `db`) and remove wording that implies normal agent workflows depend on CLI.

## Current Findings
- `README.md` still describes storage as user-level `~/.engram/memory.db` and architecture diagram references `~/.engram/`.
- `docs/USER_MANUAL.md` and `src/engram/USER_MANUAL.md` still describe central/global storage and global DB diagnostics.
- Workflow sections already emphasize MCP tools, but some wording still mixes CLI and MCP in ways that can imply CLI dependency.
- `docs/PROJECT_BRIEF.md` appears mostly aligned but will be checked for consistency-only updates if required by acceptance framing.

## Planned Changes
1. `README.md`
- Update storage model to repo-local `.engram/memory.db` as normal behavior.
- Update architecture diagram labels and supporting bullets to match repo-local project state.
- Keep MCP-first workflow guidance and clarify CLI as optional human utility only.

2. `docs/USER_MANUAL.md`
- Rewrite overview and project model sections to remove global-storage language.
- Update `engram db` description to reflect repo-local diagnostics.
- Tighten workflow narrative so normal agent execution is MCP tool/resource driven.

3. `src/engram/USER_MANUAL.md`
- Mirror `docs/USER_MANUAL.md` updates so packaged and top-level manuals stay synchronized.

4. `docs/PROJECT_BRIEF.md` (if needed)
- Apply only minimal wording adjustments needed to remain consistent with repo-local MCP-first claims.

## Validation Plan
- Search for stale global-path phrasing:
  - `rg -n "~/.engram|global database|globally outside the repository" README.md docs/USER_MANUAL.md src/engram/USER_MANUAL.md docs/PROJECT_BRIEF.md`
- Ensure manuals remain in sync:
  - `fc /N docs\\USER_MANUAL.md src\\engram\\USER_MANUAL.md` (or equivalent diff)
- Run documentation-related checks if available in project tooling:
  - `pytest -q` subset only if docs assertions exist.

## Out of Scope
- Future-phase output-contract or verification-gate documentation updates.
- Any CLI or MCP implementation refactors.
- Non-task documentation cleanup unrelated to repo-local MCP-first behavior.
