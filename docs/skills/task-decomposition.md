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

1. Read the phase doc once for full context, then extract:
- explicit goals
- acceptance criteria
- phase-level constraints
- non-goals
2. Draft a dependency graph before creating tasks:
- list candidate tasks as nodes
- mark each edge `A -> B` only when `B` cannot ship without `A`
- remove weak edges ("nice to have first") so parallel work stays parallel
3. Partition the graph into execution-ready tasks:
- each task must produce one verifiable unit of progress
- each task must have concrete files or search targets
- each task must have explicit out-of-scope boundaries
4. For each task, fill required metadata and fallback sections:
- populate first-class fields (`title`, `description`, `acceptance`, `relevant_files`, `depends_on`, optional `tags`)
- place non-schema metadata under stable `description` labels
5. Create tasks with `engram_task_create`.
6. Re-open each created task and run a quality check:
- acceptance is testable
- dependency rationale exists
- verification guidance is actionable
- out-of-scope limits are explicit

## Quality Bar

- Reject weak tasks that only contain title/description/dependency.
- Every task must include acceptance and verification intent.
- Every task must include either direct dependency references or explicit no-dependency reasoning in `description`.
- Every task must include explicit out-of-scope boundaries.

## Dependency Graph Guidance

Use this lightweight graph method to keep task ordering correct without over-serializing work:

1. Build nodes from deliverables, not implementation steps.
2. Add edges only for hard blockers:
- schema or interface preconditions
- test harness required before new assertions
- shared contract required before parallel implementers can proceed
3. Mark independent nodes as parallel-capable and avoid artificial chains.
4. Convert graph edges to `depends_on` references after task creation order is known.
5. Record "why" for each dependency in the `Dependencies:` section, including explicit "No required dependencies." when none apply.

## Example Task Shapes

Use these as templates when converting a phase doc into task payloads.

## Representative Walkthrough (Workflow Redesign)

Use this quick pass to validate that decomposition output is execution-ready for
`docs/CODEX_IMPLEMENTATION_PHASES_WORKFLOW_REDESIGN.md` Phase 10.

1. Select the phase goal and non-goals.
- Goal: add/reinforce a Task Decomposition Skill that creates complete tasks.
- Non-goals: do not implement Phase 11 draft-ready lifecycle or Phase 12 validation logic.
2. Draft dependency graph with hard blockers only.
- Node A: skill mapping and stable description-section labels.
- Node B: dependency-graph and execution-ready templates.
- Edge: `A -> B` only if templates depend on finalized mapping guidance.
3. Emit execution-ready tasks (not title-only placeholders).
- Each task must include `acceptance`, `relevant_files`, `Verification:` guidance, and `Out of scope:` boundaries.
- Each task must include either concrete `depends_on` refs or explicit "No required dependencies."
4. Run the quality bar before create/update.
- Reject any candidate that only has `title` + generic `description` + dependency.
- Reject any candidate missing testable acceptance or actionable verification commands.

If any check fails, revise the task payload before calling `engram_task_create`.

### Example A: Foundation Task (No Dependencies)

`title`
- Add verification state resolver for workflow eligibility

`acceptance`
- Resolver returns one of: missing, failed, passed, stale.
- Stale classification uses file modification checks against latest successful verification.
- Unit tests cover all four states.

`relevant_files`
- `src/engram/services/workflow/finish_eligibility.py`
- `src/engram/services/workflow/verification_state.py`
- `tests/services/workflow/test_finish_eligibility.py`

`depends_on`
- `[]`

`description` shape
```text
Objective:
Implement a service-layer verification state resolver used by workflow finish gating.

Dependencies:
No required dependencies. This is the phase foundation for later finish-tool wiring.

Verification:
Run: uv run pytest tests/services/workflow/test_finish_eligibility.py -q
Then run: uv run pytest -q

Search hints:
verify_workflow, verification_status, eligible_to_finish, stale verification

Out of scope:
Do not change MCP output formatting or workflow_finish tool responses.

Risks:
Potential false stale detections if timestamp parsing is inconsistent across helpers.
```

### Example B: Integration Task (Depends On Foundation)

`title`
- Enforce verification gate in workflow finish MCP tool

`acceptance`
- `engram_workflow_finish` blocks when verification is missing, failed, or stale.
- Blocked response provides one next action: rerun `engram_workflow_verify`.
- Existing non-verification error handling remains unchanged.

`relevant_files`
- `src/engram/mcp/server.py`
- `src/engram/services/workflow/finish.py`
- `tests/mcp/test_workflow_finish.py`

`depends_on`
- `[<foundation_task_ref>]`

`description` shape
```text
Objective:
Wire finish-time verification eligibility into the workflow_finish MCP path.

Dependencies:
Depends on <foundation_task_ref> because finish enforcement requires the verification
state classifier and shared eligibility contract.

Verification:
Run: uv run pytest tests/mcp/test_workflow_finish.py -q
Run: uv run pytest tests/services/workflow -q

Search hints:
engram_workflow_finish, format_finish_blocked, verification gate, next action

Out of scope:
Do not add memory-review checks in this task if phase scope is verification-only.
Do not introduce new task schema fields.

Risks:
Regression risk in legacy finish success path if gate interception is too broad.
```

## Tool Usage Pattern

1. Draft metadata locally from the phase doc.
2. Create the task with `engram_task_create`.
3. If dependency refs are unknown at create time, update them immediately after all related tasks exist.
4. Re-open tasks and verify they remain execution-ready, not title-only placeholders.
