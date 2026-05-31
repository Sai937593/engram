# Task Decomposition Skill

Use this skill to convert an implementation phase document into executable Engram tasks using the current `engram_task_create` schema only.

## Goal

Produce tasks that are immediately actionable and verification-ready, without inventing unsupported task fields.

## Required Metadata Per Task

- `title`: concise action-oriented task name.
- `objective/description`: the concrete implementation intent and boundary.
- `acceptance`: testable completion criteria.
- `relevant files`: specific file paths or directories to inspect/edit.
- `dependency reasoning`: what this task depends on and why.
- `verification guidance`: how success should be verified.
- `out-of-scope boundaries`: explicit exclusions to prevent scope creep.

## Field Mapping to `engram_task_create`

| Required concept | Primary field(s) | Mapping rule |
| --- | --- | --- |
| title | `title` | Put the task headline directly in `title`. |
| objective/description | `description` | Start `description` with objective, then key implementation notes. |
| acceptance criteria | `acceptance` | Store concrete, testable criteria in `acceptance`. |
| relevant files | `relevant_files` | Add normalized paths as a list of strings. |
| dependency reasoning | `depends_on`, `description` | Use `depends_on` for direct task dependency refs; keep rationale text in `description` under a `Dependencies:` section. |
| verification guidance | `description`, `acceptance` | Put exact commands/check strategy in `description` under `Verification:`. Keep outcome-level checks in `acceptance`. |
| out-of-scope boundaries | `description` | Add an `Out of scope:` section in `description`. |
| search hints | `description`, `tags` | Put grep/search keywords in `description` under `Search hints:`. Optionally include compact topical labels in `tags`. |
| risk notes | `description` | Add a `Risks:` section in `description` when the phase content indicates uncertainty or regression risk. |

## Fallback Placement Rules (No New Schema Fields)

- Do not create custom fields for `search hints`, `verification guidance`, `out-of-scope`, or `risk notes`.
- When a concept has no first-class task field, place it in structured sections inside `description`.
- Use stable section labels in `description`:
  - `Dependencies:`
  - `Verification:`
  - `Search hints:`
  - `Out of scope:`
  - `Risks:`
- Keep sections concise and deterministic so downstream validation/readiness checks can parse them consistently.

## Authoring Flow

1. Read the phase doc and split work into independent vertical tasks.
2. For each task, draft all required metadata before creating it.
3. Map metadata strictly through the table above.
4. Create the task with `engram_task_create`.
5. Re-open created tasks and confirm required metadata is present and specific.

## Quality Bar

- Reject weak tasks that only contain title/description/dependency.
- Every task must include acceptance and verification intent.
- Every task must include either direct dependency references or explicit no-dependency reasoning in `description`.
- Every task must include explicit out-of-scope boundaries.
