# Implementation Plan - Phase 7.3

## Scope
Update primary agent-facing workflow documentation so routine memory usage is presented as simple CRUD (`list/get/create/update/delete`), and remove or demote advanced lifecycle concepts (levels, tags, scope, always_include, memory types, demote, supersede) from normal guidance.

## Files
- docs/USER_MANUAL.md
- src/engram/USER_MANUAL.md
- docs/CODEX_IMPLEMENTATION_PHASES_WORKFLOW_MVP_SIMPLIFICATION.md
- docs/CODEX_HANDOFF_WORKFLOW_MVP_SIMPLIFICATION.md
- docs/adr/0002-workflow-mvp-simplification.md

## Planned changes
1. Update both USER_MANUAL copies so the "Memories" concept and workflow sections describe simple CRUD as the normal interface and avoid instructing routine lifecycle management fields/actions.
2. Adjust MCP tool reference wording to keep advanced/deprecated lifecycle semantics out of primary workflow guidance, while retaining accurate tool naming where needed.
3. In implementation/handoff docs, clearly mark advanced memory lifecycle references as historical/background and keep active guidance aligned to simple CRUD expectations.
4. In ADR 0002, keep historical context but ensure active decision and agent-facing workflow text explicitly emphasizes simple CRUD in normal operation.
5. Keep edits narrowly scoped to the listed docs and avoid unrelated workflow or service changes.

## Verification
- Run focused doc checks by inspecting updated sections for:
  - simple CRUD as normal memory interface
  - no routine guidance requiring demote/supersede/levels/tags/always_include/scope/types
  - historical references clearly isolated
- Run workflow verification gate:
  - `engram_workflow_verify`

## Risks
- Duplicate docs (`docs/` and `src/engram/`) can drift if edits are not mirrored exactly.
- Over-pruning could remove legitimate historical context needed for traceability.
- Mixed terminology (`finish` vs `finish_and_commit`) may reappear if wording updates are inconsistent.

## Done criteria
- Primary docs present memory CRUD as the routine interface.
- Normal workflow guidance no longer directs agents to manage advanced memory lifecycle fields/concepts.
- Any retained advanced lifecycle references are clearly marked as historical/background.
- `engram_workflow_verify` passes after documentation updates.
