# Implementation Plan - Task 9ccc3b0f (Phase 10.1)

## Scope
Define the Task Decomposition skill contract for turning implementation phase docs into executable Engram tasks, and map required planning metadata into currently supported task fields without inventing new schema fields.

## Constraints and Boundaries
- One-task session only: execute only task `9ccc3b0f`.
- Keep scope to contract and field mapping only.
- Exclude draft/ready lifecycle handling and task validation changes (phases 11/12).
- Preserve no-touch directories: `planning/`, `workflow/`, `.github/`.

## Investigation Plan
1. Read target workflow docs and memory-review skill reference:
- `docs/CODEX_HANDOFF_WORKFLOW_REDESIGN.md`
- `docs/CODEX_IMPLEMENTATION_PHASES_WORKFLOW_REDESIGN.md`
- `docs/skills/memory-review.md`

2. Inspect existing task schema and creation surfaces:
- Task model / supported fields in `src/engram/models/task.py`
- Task creation/update service interfaces in `src/engram/services/`
- Any decomposition/skill docs under `docs/skills/` for consistency

3. Identify destination file for the skill contract and update it with explicit mappings and fallback placements.

## Planned Changes
1. Author or update the Task Decomposition skill contract doc in the identified target location.
2. Require and define these elements in the contract:
- title
- objective/description
- acceptance criteria
- relevant files
- dependency reasoning
- verification guidance
- out-of-scope boundaries
3. Add explicit field mapping table:
- Map each required concept to existing `engram_task_create` fields.
- For concepts without direct fields (search hints, risk notes, extra verification detail), define documented fallback placement (for example: structured sections in `description` or task evidence notes) without schema expansion.

## Validation Plan
- Verify mapping aligns with actual current task model and create-tool contract in code.
- Run `engram_workflow_verify`.
- If verification fails, fix first actionable issue and rerun.

## Out of Scope
- Adding new task columns/fields.
- Implementing draft/ready lifecycle.
- Implementing runtime task validation changes.
