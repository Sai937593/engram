# ADR: First-Class Plan Workflow Standardization

- **Status:** Accepted for implementation
- **Date:** 2026-06-02
- **Plan key:** `p0004`
- **Scope:** Engram workflow model, plan lifecycle, branch/path naming, dogfooding migration, verification modes, test cleanup, and agent skills
- **Supersedes:** the previous incomplete/partial workflow-standardization direction tracked under `p0003`

## Context

Engram currently treats projects, phases, and tasks as the main workflow entities. During dogfooding, implementation plans are also real workflow units, but plan identity has been represented indirectly through project fields, branch names, and docs naming.

That creates contradictions:

- `Project` is stable repo/application identity, while implementation plans change over time.
- Branch and task-plan paths can accidentally derive from project identity instead of plan identity.
- Phase/task keys are not cleanly scoped under a real plan.
- Current-plan defaults are hard to define without a first-class active plan.
- New plan setup is multi-step, but no dedicated plan workflow owns it.
- Existing docs, tests, branches, and local DB state can continue encoding old workflow assumptions unless migration and dogfooding cleanup are explicit.

The intended workflow model is:

```text
Project -> Plan -> Phase -> Task
```

For now, Engram will support **one active plan per project**. Historical or archived plans may exist, but only the active plan drives workflow defaults.

## Decision

### 1. Add `Plan` as a first-class entity

Engram will introduce a simple `Plan` entity between `Project` and `Phase`.

Minimum fields:

| Field | Purpose |
|---|---|
| `id` | Internal DB identity |
| `key` | Canonical stable key, for example `p0004` |
| `title` | Human-readable title |
| `slug` | Optional readable slug, for example `first-class-plan-workflow-standardization` |
| `status` | Plan lifecycle state |
| `project_id` | Parent project |
| `source_doc_path` | Plan docs location, if available |
| `created_at` / `updated_at` | Audit timestamps |

Initial statuses:

```text
draft
active
review_pending
done
archived
cancelled
```

Only one plan may be `active` per project.

### 2. Move active-plan identity out of `Project.plan_key`

`Project` remains stable repo/application identity. It should not own changing implementation-plan identity.

The active plan should be represented through a project-level pointer or equivalent relationship:

```text
project.current_plan_id -> plans.id
```

Workflow branch/path derivation must use the active `Plan.key`, not the project ID and not fallback project fields.

### 3. Use one canonical key system everywhere

Canonical key format:

```text
Plan:  pNNNN  # example: p0004
Phase: phNN   # example: ph01
Task:  tNN    # example: t01
```

Use the same keys in:

- branch names
- task-plan paths
- plan docs references
- MCP output
- phase/task labels
- workflow status output

For this plan:

```text
Plan key: p0004
```

Branch naming:

```text
plan/p0004
plan/p0004/ph01
plan/p0004/ph01/t01   # only if task-level branches are used
```

Task-plan path format:

```text
.engram/task-plans/p0004/ph01/t01/task-plan.md
```

Plan docs path:

```text
docs/plans/p0004/
  adr.md
  implementation-phases.md
```

Global ADRs remain only for cross-plan architecture decisions intended to outlive one implementation plan:

```text
docs/adr/
```

### 4. Keep plan tools plan-scoped

Plan tools manage plan identity, state, docs, and activation only.

Minimum tools:

| Tool | Responsibility |
|---|---|
| `engram_plan_current` | Show the current active plan |
| `engram_plan_create` | Create/register a plan |
| `engram_plan_activate` | Make one plan active for the project |
| `engram_plan_update` | Update plan metadata/status/source doc |
| `engram_plan_list` | List plans, defaulting to current/recent |
| `engram_plan_get` | Show full plan detail |

Plan tools must **not** create or update phases/tasks. Phase/task creation and updates belong to the task decomposition workflow.

### 5. Add a dedicated plan skill

Plan setup is multi-step and needs a dedicated skill.

The plan skill owns:

- detecting or registering a new plan
- assigning the canonical plan key
- linking the plan docs path
- activating the plan
- creating/checking out the plan branch
- confirming workflow status points to the active plan

The plan skill does **not** create or update phases/tasks.

Skill boundary:

| Skill | Owns |
|---|---|
| Plan skill | plan identity, docs, activation, plan branch |
| Task decomposition skill | phases, tasks, keys, ordering, acceptance criteria |
| Task execution skill | one task, task-plan, edits, task verification, finish |
| Phase review skill | full verification, phase review, phase completion |

### 6. Keep task decomposition separate

Once task decomposition is accepted, phases/tasks are considered workflow records. They may still be changed through an explicit planning/decomposition operation, but the task execution workflow should not silently delete, split, or reorder them.

This preserves traceability for:

- branches
- task-plan paths
- verification history
- phase lifecycle
- finish/review behavior

### 7. Make task-plans grounded and reviewable

The task-plan must not be ceremonial. It must only be written after targeted repo investigation.

Required task-plan sections:

```text
## Investigation
- Files inspected:
- Current behavior:
- Related tests:
- Risks / unknowns:

## Intended Edit Set
- Files expected to change:
- Behavior changes:

## Verification Targets
- Task-mode checks:
- Relevant pytest targets:
```

If the task-plan is unsatisfactory, the user must be able to ask the agent to revise it before editing begins. The agent should revise the same task-plan, not create competing task-plan files.

### 8. Remove low hard caps from workflow-critical outputs

Do not apply low hard caps to critical task/phase workflow fields.

| Output type | Cap policy |
|---|---|
| Current task detail | No low cap |
| Acceptance criteria | No low cap |
| Verification instructions | No low cap |
| Relevant files | High threshold only |
| Current-plan task list | High threshold or uncapped |
| Memories | Capped |
| Archived/history lists | Capped |

If output is truncated, the tool must explicitly report that truncation happened.

### 9. Add workflow verification modes

`engram_workflow_verify` should accept an explicit mode:

```text
mode="task"
mode="phase"
```

Default:

```text
mode="task"
```

Task mode is optimized for fast feedback. Phase mode is full verification before phase review/completion.

Initial implementation should avoid advanced optimizations such as `xdist`, `testmon`, persistent watchers, and custom pytest plugins. Keep verification simple and reliable.

### 10. Treat migrations and dogfooding cleanup as first-class work

This plan changes Engram while Engram is being used to manage itself. Therefore migration work is part of the implementation, not optional cleanup.

Required migration/dogfood principles:

- Existing local DBs must migrate safely.
- Existing project/phase/task rows must remain queryable.
- Existing p0003-era state should be preserved as historical or inactive state where applicable, not silently rewritten to `p0004`.
- The new `p0004` plan becomes active through the plan workflow.
- Old docs/tests/skills that contradict the new model must be archived, rewritten, or deleted based on relevance.

### 11. Reorganize tests around current behavior

The test suite should describe the current product contract, not preserve obsolete workflow designs.

Rules:

| Test type | Action |
|---|---|
| Current intended behavior | Keep |
| Legacy behavior still intentionally supported | Keep and mark clearly |
| Old behavior now rejected | Delete |
| Useful scenario with outdated assertions | Rewrite |
| Duplicate coverage | Consolidate |

The flat `tests/` layout should be reorganized into behavior-focused subdirectories so targeted verification is easier for both humans and agents.

## Consequences

### Positive

- Plan identity is explicit and no longer overloaded onto `Project`.
- Branches, docs, task-plan paths, and MCP output can use one key system.
- New plan setup becomes repeatable through a plan skill/tool surface.
- Task decomposition remains cleanly separated from plan activation.
- Dogfooding migration risk is handled deliberately.
- Task execution becomes more grounded and less ceremonial.
- Verification gains fast task mode and full phase mode without fragile advanced tooling.

### Costs

- Requires DB migration and backfill logic.
- Requires updates across services, MCP tools, docs, skills, tests, and workflow formatting.
- Requires cleanup of old p0003-era docs/tests/instructions that conflict with the new model.
- Adds one more first-class entity to the system.

## Rejected alternatives

### Keep `plan_key` on `Project`

Rejected because projects are stable repo identities while plans change over time. This would continue mixing two different concepts.

### Add `plan_key` to project initialization

Rejected because plans are created over the life of a project. Plan setup should be handled by plan-level operations, not project initialization.

### Let the plan skill create phases/tasks

Rejected because task decomposition already owns phases/tasks. Mixing the responsibilities would make plan activation too powerful and harder to reason about.

### Use separate naming systems for branches and paths

Rejected because short branch names and long path names would create confusion. The canonical key system should be compact enough to use everywhere.

### Add advanced pytest optimizations immediately

Rejected for this plan. `xdist`, `testmon`, watchers, and custom plugins may be useful later, but first we should improve simple verification modes, test layout, markers, and task-plan test targets.
