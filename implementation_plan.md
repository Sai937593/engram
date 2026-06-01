# Implementation Plan - Phase 8.4 Batch Memory Ops Docs Refresh

## Scope
Refresh agent-facing documentation and templates so memory workflow guidance includes batch helpers:
- `engram_memory_update_many`
- `engram_memory_delete_many`

Keep guidance concise, workflow-focused, and aligned with MVP contracts.

## Files to Change
- `docs/USER_MANUAL.md`
- `src/engram/USER_MANUAL.md`
- `agent-files/skills/engram-phase-review-template.md`
- `agent-files/skills/engram-task-decomposition-template.md` (only if memory tool listings or guidance references require consistency wording)
- `README.md`

## Planned Implementation
1. Update both USER_MANUAL copies:
- Add `engram_memory_update_many` and `engram_memory_delete_many` to the memory tool inventory.
- Update phase-level memory review step wording to mention CRUD plus batch update/delete helpers.
- Preserve compact workflow framing and avoid lifecycle-governance jargon (tags, levels, supersede, demote, always_include, scope, memory types) in normal agent guidance.
2. Update phase review skill template tool list and memory curation wording to include/allow batch update/delete helpers while keeping existing simple CRUD-first framing.
3. Review decomposition template for any memory tool list references and adjust only if required for consistency.
4. Update README MCP/tool workflow references:
- Prefer `engram_workflow_finish_and_commit` naming with alias note if already referenced.
- Mention batch memory helpers where memory operations are summarized.
5. Ensure root `AGENTS.md` is untouched and no `.engram/reports/*.md` files are created.

## Planned Verification
1. Run targeted checks for expected strings:
- Confirm both batch tool names appear in all intended files.
- Confirm disallowed lifecycle-governance terms are not newly introduced in agent-facing workflow sections.
2. Run repository verification gate via workflow tool:
- `engram_workflow_verify`

## Non-goals
- No Python/service/tool implementation changes.
- No CLI behavior changes.
- No workflow redesign beyond wording alignment.