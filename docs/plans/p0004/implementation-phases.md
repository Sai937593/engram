# Implementation Phases: First-Class Plan Workflow Standardization

- **Plan key:** `p0004`
- **Status:** Draft for implementation review
- **Date:** 2026-06-02
- **Primary goal:** migrate Engram from implicit `Project -> Phase -> Task` workflow assumptions to explicit `Project -> Plan -> Phase -> Task`, while keeping dogfooding state coherent.

## Target repository paths for these docs

Place these files in the Engram repository at:

```text
docs/plans/p0004/adr.md
docs/plans/p0004/implementation-phases.md
```

## Global invariants

These invariants apply across all phases.

1. `Project` is stable repo/application identity.
2. `Plan` is first-class implementation-plan identity.
3. Only one plan is active per project for now.
4. Branches, docs, task-plan paths, and MCP output must use the same canonical key system:

   ```text
   pNNNN / phNN / tNN
   ```

   For this plan:

   ```text
   p0004 / ph01 / t01
   ```

5. Plan tools and the plan skill must not create or update phases/tasks.
6. Task decomposition owns phase/task creation, updates, ordering, acceptance criteria, and keys.
7. Task execution must create a grounded task-plan before editing.
8. The user must be able to reject an unsatisfactory task-plan and ask the agent to revise it.
9. Workflow-critical output should not use low hard caps.
10. Memories remain capped.
11. Dogfood migrations and stale repo cleanup are part of the work, not optional cleanup.
12. Advanced pytest optimizations such as `xdist`, `testmon`, persistent watchers, and custom plugins are deferred.

## Target repository conventions

### Plan docs

```text
docs/plans/p0004/
  adr.md
  implementation-phases.md
```

### Global ADRs

```text
docs/adr/
```

Use global ADRs only for cross-plan architectural decisions intended to outlive a single implementation plan.

### Branches

```text
plan/p0004
plan/p0004/ph01
plan/p0004/ph01/t01   # only if task-level branches are used
```

### Task plans

```text
.engram/task-plans/p0004/ph01/t01/task-plan.md
```

## Phase 1 — Plan Entity and Migration Foundation

### Goal

Introduce the `Plan` entity and migrate existing local/dogfood state without breaking existing projects, phases, or tasks.

### Tasks

#### P1-T1. Add the `Plan` model/table

Add a first-class plan table/model with at least:

```text
id
key
title
slug
status
project_id
source_doc_path
created_at
updated_at
```

Initial valid statuses:

```text
draft
active
review_pending
done
archived
cancelled
```

Acceptance criteria:

- Plans can be created and queried.
- Plan keys are unique within the appropriate project scope.
- Status validation exists.
- Model-level tests cover required fields and invalid statuses.

#### P1-T2. Add active-plan relationship on project

Add `project.current_plan_id` or equivalent active-plan pointer.

Acceptance criteria:

- A project can identify its current active plan.
- Workflow code can resolve the active plan without reading `Project.plan_key`.
- Empty projects can exist without an active plan until a plan is created/activated.

#### P1-T3. Migrate existing project-level plan state

Migrate current `Project.plan_key` usage into the new `Plan` entity.

Dogfood-specific expectations:

- Existing p0003-era state is preserved as `p0003` where detectable.
- New `p0004` state is created/activated through the plan workflow, not by silently rewriting old state.
- Existing phases/tasks attach to the correct migrated plan where possible.
- Fallback/default project-derived plan keys do not become silently accepted workflow keys.

Acceptance criteria:

- Existing DB without plans migrates successfully.
- Existing project with a real plan key gets a matching plan record.
- Existing fallback/default keys are detected and handled explicitly.
- Existing phase/task rows remain queryable after migration.

#### P1-T4. Add migration tests

Test at least:

- fresh empty DB
- existing DB without plans
- existing project with explicit plan key
- existing project with fallback/default plan key
- existing phases/tasks backfilled to a plan
- idempotent migration behavior

Acceptance criteria:

- Running migrations twice does not duplicate plans or corrupt links.
- Existing dogfood data remains coherent.

## Phase 2 — Plan Tools and Plan Skill Boundary

### Goal

Add a small plan tool surface and a clear plan skill that manages plan identity, state, docs, and branch setup only.

### Tasks

#### P2-T1. Add plan tools

Add:

```text
engram_plan_current
engram_plan_create
engram_plan_activate
engram_plan_update
engram_plan_list
engram_plan_get
```

Acceptance criteria:

- `engram_plan_current` returns the active plan for the current project.
- `engram_plan_create` can register a plan without activating it unless requested.
- `engram_plan_activate` enforces only one active plan per project.
- `engram_plan_update` updates metadata/status/source doc without touching phases/tasks.
- `engram_plan_list` defaults to current/recent useful output.
- `engram_plan_get` returns full detail for a selected plan.

#### P2-T2. Enforce active-plan validation

Workflow execution must require an active plan when operating on phases/tasks.

Acceptance criteria:

- Branch/path derivation fails if no active plan exists.
- Branch/path derivation fails if the plan key is missing or invalid.
- Workflow execution never falls back to project ID for plan identity.

#### P2-T3. Add the plan skill

Create a plan skill with this responsibility boundary:

```text
- detect/register a new plan
- assign canonical plan key
- link docs path
- activate the plan
- create/check out the plan branch
- confirm workflow status points to the active plan
```

The plan skill must explicitly not create/update phases or tasks.

Acceptance criteria:

- Skill is short, direct, and unambiguous.
- Skill tells the agent what tool to call first.
- Skill states stop conditions.
- Skill clearly delegates phase/task creation to task decomposition.

#### P2-T4. Add plan activation tests

Acceptance criteria:

- Creating multiple plans is allowed.
- Activating a new plan deactivates or transitions the previous active plan according to the chosen rule.
- `engram_plan_current` reports exactly one active plan.
- Existing phases/tasks remain associated with their original plan.

## Phase 3 — Docs Structure, Naming, and Dogfood Cleanup

### Goal

Remove contradictions between old workflow docs and the new plan-scoped model.

### Tasks

#### P3-T1. Place plan-scoped docs under `docs/plans/p0004/`

Use:

```text
docs/plans/p0004/
  adr.md
  implementation-phases.md
```

Acceptance criteria:

- The p0004 decision and implementation docs are co-located.
- Old duplicate plan docs are removed or archived if they are no longer authoritative.
- Links/references are updated.

#### P3-T2. Preserve global ADRs only where appropriate

Keep `docs/adr/` only for cross-plan architecture decisions.

Acceptance criteria:

- Plan-specific ADR content is not duplicated in global ADRs.
- Any global ADRs left in place are genuinely cross-plan.

#### P3-T3. Standardize canonical key references

Replace inconsistent examples with:

```text
p0004 / ph01 / t01
```

Acceptance criteria:

- Docs, examples, skills, tests, and MCP outputs use the canonical key format.
- No examples derive plan identity from project ID.

#### P3-T4. Archive or delete obsolete workflow docs

Review old workflow redesign docs, p0003-era files, and root-level implementation docs.

Acceptance criteria:

- Docs that are historically useful but no longer authoritative are archived.
- Docs that are duplicate/noisy/contradictory are deleted.
- The active plan docs are unambiguous.

## Phase 4 — Workflow Status, Start, and Task-Plan Grounding

### Goal

Make task execution reliable under the new plan model.

### Tasks

#### P4-T1. Add or update `engram_workflow_status`

The tool should show the current project, active plan, active/review phase, current task, branch expectation, and next valid workflow action.

Acceptance criteria:

- Output resolves through `Project -> active Plan -> Phase -> Task`.
- Missing active plan is reported clearly.
- No branch/path output uses fallback project identity.

#### P4-T2. Update workflow start context resolution

`engram_workflow_start` should derive context from the active plan.

Acceptance criteria:

- Branch name uses active plan key and phase/task keys.
- Task-plan path uses active plan key and phase/task keys.
- Start output includes enough context for the agent to work without low hard caps on critical fields.

#### P4-T3. Create or update task-plan stub at workflow start

Task-plan path format:

```text
.engram/task-plans/p0004/ph01/t01/task-plan.md
```

Acceptance criteria:

- Missing parent directories are created.
- Existing task-plan is not overwritten.
- Stub contains required grounded sections.
- Output tells the agent whether the task-plan was created or already existed.

#### P4-T4. Require grounded task-plan sections

Required sections:

```text
## Investigation
## Intended Edit Set
## Verification Targets
```

Acceptance criteria:

- Task execution instructions require targeted repo investigation before writing the task-plan.
- The task-plan names inspected files, intended edit files, current behavior, verification targets, and risks/unknowns.
- User can reject and request revision before editing.

#### P4-T5. Remove low hard caps from workflow-critical output

Acceptance criteria:

- Critical task detail, acceptance criteria, verification instructions, branch/path, and task-plan path are not hidden behind low caps.
- Memories remain capped.
- Any truncation is explicitly disclosed.

## Phase 5 — Verification and Test Suite Cleanup

### Goal

Make verification fast enough for task execution and trustworthy enough for phase review, without advanced pytest tooling.

### Tasks

#### P5-T1. Add `engram_workflow_verify(mode="task" | "phase")`

Default:

```text
mode="task"
```

Acceptance criteria:

- Unknown modes are rejected clearly.
- Task mode and phase mode produce visibly different command sets.
- Existing callers that omit mode use task mode.

#### P5-T2. Implement task-mode verification

Task mode should favor simple optimizations:

```text
ruff format <changed-python-files>
ruff check <changed-python-files> --fix
py_structure --changed
pytest <task-plan-test-targets> -x --tb=short
pytest --lf -x --tb=short   # only as a failure-fixing helper
```

Acceptance criteria:

- Task mode avoids full-suite pytest by default.
- Task mode uses pytest targets from the task-plan when available.
- Task mode fails clearly when no useful target can be determined.

#### P5-T3. Implement phase-mode verification

Phase mode should be full and conservative:

```text
ruff format .
ruff check .
py_structure --all
pytest tests/ -m "not slow" --tb=short
```

Acceptance criteria:

- Phase mode does not use selective/last-failed-only verification.
- Phase mode is suitable before phase review/completion.

#### P5-T4. Reorganize tests into subdirectories

Move from flat `tests/` to behavior-focused folders such as:

```text
tests/
  db/
  models/
  services/
  workflow/
  mcp/
  cli/
  regression/
```

Acceptance criteria:

- Pytest collection still works.
- Test paths are configured explicitly if needed.
- Agents can identify relevant tests by feature area.

#### P5-T5. Split huge workflow/e2e files by behavior

Example target structure:

```text
tests/workflow/e2e/test_finish.py
tests/workflow/e2e/test_verify.py
tests/workflow/e2e/test_memory_review.py
tests/workflow/e2e/test_transition_guidance.py
```

Acceptance criteria:

- Slow end-to-end behavior remains covered.
- Normal task-mode verification can avoid unrelated e2e tests.
- Test names and locations map to product behavior.

#### P5-T6. Delete or rewrite irrelevant tests

Use relevance to the current product state, not age.

Acceptance criteria:

- Tests for current behavior are kept.
- Tests for removed behavior are deleted.
- Tests with useful scenarios but outdated assertions are rewritten.
- Duplicate coverage is consolidated.

## Phase 6 — Skills and Agent Instruction Cleanup

### Goal

Remove workflow ambiguity for dogfooding and give agents concise, useful rails.

### Tasks

#### P6-T1. Update/create workflow skills

Required skills:

```text
plan skill
task decomposition skill
task execution skill
phase review skill
```

Acceptance criteria:

- Each skill has a clear first action.
- Each skill has required tool calls or checks.
- Each skill has hard do/don't rules.
- Each skill has stop conditions.
- Each skill avoids long historical explanations.

#### P6-T2. Remove obsolete workflow references

Search and clean references to:

```text
implementation_plan.md
old branch naming
merge-to-main assumptions
project-level plan_key as workflow identity
old p0003 docs as current instructions
```

Acceptance criteria:

- Current instructions point to `Project -> Plan -> Phase -> Task`.
- Agents are not told to follow obsolete workflow paths.
- Skills do not mix old and new branch/path conventions.

#### P6-T3. Add consistency checks for banned old terms

Add simple checks where useful for docs/skills/tests consistency.

Acceptance criteria:

- Known obsolete terms are detected in active docs/skills.
- Historical/archive docs are excluded from active-doc checks if needed.
- Checks are simple and maintainable.

## Final acceptance criteria for p0004

The plan is complete when:

1. `Plan` is a first-class entity.
2. A project can have exactly one active plan for workflow defaults.
3. Plan tools manage only plan identity/state/docs/activation.
4. Plan skill exists and does not create/update phases/tasks.
5. Task decomposition remains responsible for phases/tasks.
6. Branch and task-plan paths use the canonical key system.
7. `engram_workflow_status` reports current plan/phase/task state clearly.
8. `engram_workflow_start` creates or references a grounded task-plan path.
9. The user can request task-plan revision before editing.
10. `engram_workflow_verify` supports `task` and `phase` modes.
11. Tests are reorganized enough to support targeted verification.
12. Obsolete p0003-era workflow contradictions are archived, rewritten, or deleted.
13. Existing dogfood DB/data migrates safely and remains coherent.
