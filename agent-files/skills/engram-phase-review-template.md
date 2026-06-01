# Engram Phase Review Skill

Use this skill when the user says a phase is complete, asks to review a phase, or asks to prepare for the next phase.

## Goal

Review completed phase work, clean up durable memory using simple CRUD memory tools, and prepare a concise handoff without assuming a merge target.

## Available Tools

Use simplified phase and memory tools:

- `engram_phase_list`
- `engram_phase_update`
- `engram_phase_complete`
- `engram_task_list`
- `engram_task_get`
- `engram_memory_list`
- `engram_memory_get`
- `engram_memory_create`
- `engram_memory_update`
- `engram_memory_delete`
- `engram_memory_update_many` (for batch updates)
- `engram_memory_delete_many` (for batch deletes)

Do not use raw SQLite or ad hoc Python database scripts.
Do not use any special phase memory review start tool; use only the normal tools listed above.

## Review Steps

1. **Identify the Phase**: Locate the completed or target phase.
2. **Review Task Outcomes**: Verify that all tasks in the phase are completed and meet their acceptance criteria.
3. **Audit Project Memory**:
   - Search or list existing memories to find relevant project knowledge.
   - Determine what durable project lessons or rules should be persisted, updated, or removed.
   - Keep memory review as phase-level curation; do not treat it as a per-task finish gate.
4. **Curate Memories**:
   - Create new memories for core lessons, architecture decisions, or stable constraints.
   - Update or delete stale or duplicate memories using simple CRUD tools.
   - Keep memory changes minimal and focused.
5. **Update Agent Instructions**:
   - Update the root `AGENTS.md` ONLY when a stable, repository-wide project rule, guardrail, or convention has changed.
6. **Handoff & Next Steps**:
   - Prepare a brief phase summary.
   - Ask the user which branch or target to merge into if a branch transition is needed.
   - Stop and await further instructions.

## Memory Curation Rules

Create or update memory only for durable knowledge, such as:

- Major architectural decisions.
- Recurring codebase constraints or boundaries.
- Non-obvious implementation facts or workarounds.
- Crucial lessons that affect future phases.

Do not create memory for:

- Temporary task notes or step-by-step progress.
- Obvious facts easily seen in the code.
- General coding advice not specific to this repository.

Memory review is done at the phase level. The active task loop does not enforce per-task memory-review gates.

## Branch Transitions

Do not assume the target branch is `main`. Always ask the user to clarify the target:

"Which branch should this be merged or transitioned into?"

## Output Style

Return a concise summary covering:

- The reviewed phase.
- List of tasks completed.
- Memory changes made (created, updated, or deleted).
- `AGENTS.md` changes made, if any.
- Branch/merge recommendation.
- Next required user decision.
