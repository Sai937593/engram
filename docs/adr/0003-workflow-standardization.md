# ADR 0003: Workflow Standardization and Agent Predictability

## Status

Accepted

## Date

2026-06-02

## Context

Engram's workflow MVP simplification introduced a smaller task loop:

```text
start -> implement -> verify -> finish_and_commit
```

The implementation is mostly aligned with ADR 0002, but the next iteration needs to standardize workflow behavior so Codex/agent execution is predictable across plans, phases, tasks, skills, and MCP tools.

The remaining issues are:

1. Active planning documents, historical handoffs, implementation plans, ADRs, and skill files are spread across multiple locations.
2. Plan, phase, and task names are not deterministic enough for long-running multi-iteration work.
3. The workflow branch selected by `engram_workflow_start` is currently derived from phase titles rather than explicit plan/phase keys.
4. Phase status does not clearly represent the state after all phase tasks are complete but before phase review.
5. Skills need one current-state resolver instead of repeatedly calling low-level list tools.
6. Low-level task, phase, and memory tool outputs are too noisy or underspecified for skill agents.
7. Workflow start output still contains outdated guardrail-heavy sections.
8. Normal memory tools still expose advanced lifecycle concepts that should not be part of the default agent-facing interface.
9. `py_structure` currently checks staged files, while `engram_workflow_verify` stages files after checks pass. This can miss unstaged Python changes during verify.

## Decision

Adopt a numbered plan/phase/task convention, reorganize active planning documents, introduce explicit plan/phase/task keys, update workflow branch naming, add a review-pending phase state, introduce a workflow status resolver, refine low-level tool outputs, and simplify agent-facing surfaces.

## Plan, phase, and task naming

Use deterministic keys at all levels.

### Plan key

```text
plan-0003-workflow-standardization
```

Plan display title:

```text
[PLAN-0003] Workflow Standardization
```

### Phase key

```text
ph01-planning-docs-and-naming
ph02-phase-lifecycle-and-status
ph03-low-level-tool-refinement
ph04-output-and-memory-surface
ph05-docs-tests-and-skills
```

Phase display title format:

```text
[PLAN-0003 PH01] Planning docs and naming
```

### Task key

```text
t01-migrate-planning-docs
t02-update-naming-conventions
```

Task display title format:

```text
[PLAN-0003 PH01 T01] Migrate planning docs
```

## Explicit keys

Add first-class key fields instead of parsing display titles.

Recommended fields:

```text
projects.plan_key
phases.key
tasks.key
```

If the current project model is not the right place for `plan_key`, use the smallest project-level or workflow-level storage point that can reliably identify the active plan.

Rules:

1. Code must not parse display titles to derive plan, phase, or task identity.
2. Display titles are for humans.
3. Keys are for branch names, paths, filtering, and tool output.
4. Keys must be unique within their expected scope:
   - `plan_key` unique per project history
   - `phase.key` unique within a plan
   - `task.key` unique within a phase

## Branch convention

The plan branch is created from the current MVP simplification branch:

```text
base branch: feat/workflow-mvp-simplification
plan branch: feat/plan-0003-workflow-standardization
```

Optional phase branches may be created from the plan branch:

```text
feat/plan-0003-ph01-planning-docs-and-naming
feat/plan-0003-ph02-phase-lifecycle-and-status
feat/plan-0003-ph03-low-level-tool-refinement
feat/plan-0003-ph04-output-and-memory-surface
feat/plan-0003-ph05-docs-tests-and-skills
```

Phase branches are merged back into the plan branch after phase review. The plan branch is merged into the selected target branch only after all phases are reviewed.

## Workflow branch naming

Update the workflow code used by `engram_workflow_start` to select or create the phase branch.

The target phase branch format is:

```text
feat/<plan_key>-<phase_key>
```

Example:

```text
feat/plan-0003-ph02-phase-lifecycle-and-status
```

The branch name must be derived from explicit keys:

```text
plan_key + phase.key
```

It must not be derived from display titles.

Fallback behavior:

1. If the phase has no key, fail with an actionable error.
2. If the plan key is missing, fail with an actionable error.
3. Avoid silent fallback to `feat/misc` for normal planned workflow tasks.

A fallback branch may remain only for legacy/unphased tasks, but the output must clearly state that a fallback was used.

## Documentation structure

Active implementation plans live under `docs/plans/`.

```text
docs/
  adr/
    0002-workflow-mvp-simplification.md
    0003-workflow-standardization.md

  plans/
    plan-0003-workflow-standardization/
      implementation-phases.md

  archive/
    plan-0002-workflow-mvp-simplification/
      CODEX_HANDOFF_WORKFLOW_MVP_SIMPLIFICATION.md
      CODEX_IMPLEMENTATION_PHASES_WORKFLOW_MVP_SIMPLIFICATION.md

  USER_MANUAL.md
```

Root-level `docs/CODEX_*` files should no longer be used for active plans.

Historical handoff and implementation files should be archived, not deleted, when they may still explain prior behavior.

## Agent file and skill structure

`agent-files/skills/` is the source of truth for skill templates.

```text
agent-files/
  README.md
  root-agents-template.md
  skills/
    engram-start-task-template.md
    engram-task-decomposition-template.md
    engram-phase-review-template.md
```

`docs/skills/` should be removed, archived, or replaced with a pointer to `agent-files/skills/`.

## `.engram/` runtime structure

Keep the runtime structure minimal.

```text
.engram/
  memory.db

  task-plans/
    plan-0003-workflow-standardization/
      ph01-planning-docs-and-naming/
        t01-migrate-planning-docs/
          task-plan.md
```

Do not add these folders in this iteration:

```text
.engram/handoffs/
.engram/cache/verify/
```

## Per-task plan file

Use:

```text
task-plan.md
```

Do not use:

```text
implementation.md
implementation-plan.md
```

Those names conflict with higher-level implementation documents.

A task plan may optionally include Markdown frontmatter:

```md
---
plan_key: plan-0003-workflow-standardization
phase_key: ph01-planning-docs-and-naming
task_key: t01-migrate-planning-docs
---

# Task Plan
```

## Phase status lifecycle

Add `review_pending` as a phase status.

Supported phase statuses:

```text
planned
active
review_pending
done
blocked
cancelled
```

Human display labels:

```text
planned         -> Planned
active          -> Active
review_pending  -> To be reviewed
done            -> Done
blocked         -> Blocked
cancelled       -> Cancelled
```

Lifecycle:

```text
planned -> active -> review_pending -> done
```

Behavior:

1. Starting the first task in a planned phase automatically moves the phase to `active`.
2. Finishing the last task in an active phase automatically moves the phase to `review_pending`.
3. Completing phase review moves the phase from `review_pending` to `done`.
4. Do not add a separate `reviewed` terminal status. In Engram, `done` means phase review is complete.

## Workflow status resolver

Add:

```text
engram_workflow_status
```

This tool should become the first tool used by all Engram workflow skills.

It should return:

```yaml
ok: true

project:
  id:
  name:

plan:
  key:

active_phase:
  id:
  key:
  title:
  status:

review_phase:
  id:
  key:
  title:
  status:

active_task:
  id:
  key:
  title:
  status:

next_task:
  id:
  key:
  title:
  status:

counts:
  phases:
    planned:
    active:
    review_pending:
    done:
    blocked:
    cancelled:
  tasks:
    open:
    in_progress:
    blocked:
    done:
    cancelled:

next_action:
  tool:
  reason:
```

## Low-level tool output contract

Refine low-level MCP tools so skill agents can query state directly without repeated exploratory calls.

Every list tool should return:

```yaml
ok: true
filters:
  ...
count:
items:
next_action:
```

Every compact item should include stable scan fields:

```yaml
id:
key:
title:
status:
```

Task items should also include:

```yaml
phase_id:
phase_key:
phase_title:
is_verified:
```

Phase items should also include derived markers:

```yaml
current:
review_candidate:
next_planned:
```

Memory items should remain compact by default and should not expose advanced lifecycle fields unless explicitly requested by an internal/debug view.

## Task tool argument direction

`engram_task_list` should support:

```text
status: open | in_progress | blocked | done | cancelled | all
phase_ref: string | null
scope: current | review_pending | all
view: compact | detail
```

Default behavior should be optimized for current workflow context.

## Phase tool argument direction

`engram_phase_list` should support:

```text
status: planned | active | review_pending | done | blocked | cancelled | all
view: compact | detail
```

## Memory tool argument direction

`engram_memory_list` should support:

```text
query: string | null
limit: int
view: compact | detail
```

The normal agent-facing memory surface should hide:

```text
tags
levels
demote
supersede
always_include
scope
memory types
```

## Verification decision

Do not add verification profiles or additional workflow verification tools in this iteration.

Keep:

```text
engram_workflow_verify
```

The tool may remain slow for now.

However, fix the correctness issue in `py_structure` by adding:

```text
--changed
```

Default behavior remains staged-only for hook compatibility.

`--changed` checks:

1. staged Python files
2. unstaged modified Python files
3. untracked Python files

`engram_workflow_verify` should call:

```bash
uv run python -m engram.hooks.py_structure --changed
```

## Task decomposition rule

The task decomposition skill must create the fewest tasks necessary to complete a phase safely.

A phase may contain exactly one task when:

1. the work is cohesive
2. affected files are limited
3. acceptance criteria can be verified together
4. one Codex implementation session can complete it without losing context

Split only when there are separate acceptance gates, risk areas, subsystems, or review points.

## Consequences

### Positive

- Agents can reliably determine current phase/task state.
- Historical docs stop confusing active implementation.
- Phase review becomes explicit through `review_pending`.
- Naming remains deterministic across many Engram iterations.
- Workflow branch names are predictable and match the plan/phase model.
- Low-level tool outputs become useful for skills, not just humans.
- Runtime `.engram/` structure remains simple.
- Verification correctness improves without adding new verify complexity.

### Negative

- Requires migrations for phase status and explicit key fields.
- Requires workflow branch derivation changes.
- Requires docs and skill template updates.
- Requires tests across workflow, phase, task, memory, and MCP tool surfaces.
- Requires care to avoid breaking legacy data during status normalization.

## Non-goals

This iteration does not add:

1. verify profiles
2. separate `workflow_check`
3. separate `phase_verify`
4. verify result caching
5. handoff documents
6. a new memory review gate
7. separate terminal `reviewed` phase status
