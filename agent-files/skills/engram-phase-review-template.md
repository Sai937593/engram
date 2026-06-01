# Engram Phase Review Skill

Use this skill when the user says a phase is complete, asks to review a phase, or asks to prepare for the next phase.

This skill is written for the current redesign branch state. Do not call future simplified tools such as `engram_memory_list`, `engram_memory_update_many`, or `engram_memory_delete_many` until they exist.

## Goal

Review completed phase work, clean up durable memory using current MCP tools, and prepare a concise handoff. Do not merge branches unless the user explicitly selects a target branch.

## Current available tools

Use current phase and memory tools such as:

- `engram_phase_list`
- `engram_phase_update`
- `engram_phase_complete`
- `engram_task_list`
- `engram_task_get`
- `engram_memory_search`
- `engram_memory_create`
- `engram_memory_get`
- `engram_memory_update`
- `engram_memory_supersede`
- `engram_memory_demote`
- `engram_memory_archive`
- `engram_memory_delete`

Tool availability may vary by branch. If a listed tool is unavailable, use the closest existing Engram MCP tool. Do not use raw SQLite or ad hoc Python database scripts.

## Review steps

1. Identify the active or target phase.
2. Review completed tasks in the phase.
3. Search existing memories for relevant project knowledge.
4. Decide whether any durable memory should be created, updated, superseded, archived, demoted, or deleted using current tools.
5. Keep memory changes minimal.
6. Update root `AGENTS.md` only when a stable project rule, guardrail, or convention changed.
7. Prepare a short phase summary.
8. Ask the user which branch or target to merge into if a merge/transition is needed.
9. Stop after presenting the handoff unless the user gives the next action.

## Memory review rules

Create or update memory only for durable knowledge, such as:

- architectural decisions
- recurring constraints
- non-obvious implementation facts
- important lessons that affect future tasks

Do not create memory for:

- temporary task notes
- obvious facts
- details already clear from code
- one-off debugging observations

Use current memory lifecycle tools. Do not manually inspect `.engram/memory.db`.

## Branch rule

Do not assume the target branch is `main`.

When a phase transition needs a merge or branch handoff, ask:

"Which branch should this be merged or transitioned into?"

## Output style

Return:

- phase reviewed
- tasks completed or remaining
- memory changes made
- `AGENTS.md` changes made, if any
- branch/merge recommendation
- next required user decision
