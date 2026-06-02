# Implementation Phases: Plan 0003 Workflow Standardization

## Metadata

```yaml
plan_key: plan-0003-workflow-standardization
plan_title: "[PLAN-0003] Workflow Standardization"
base_branch: feat/workflow-mvp-simplification
plan_branch: feat/plan-0003-workflow-standardization
adr: docs/adr/0003-workflow-standardization.md
implementation_plan: docs/plans/plan-0003-workflow-standardization/implementation-phases.md
```

## Exact branch instructions

Create the plan branch from:

```text
feat/workflow-mvp-simplification
```

Create this branch:

```text
feat/plan-0003-workflow-standardization
```

Commands:

```bash
git fetch origin
git checkout feat/workflow-mvp-simplification
git pull origin feat/workflow-mvp-simplification
git checkout -b feat/plan-0003-workflow-standardization
git push -u origin feat/plan-0003-workflow-standardization
```

Optional phase branches should be created from:

```text
feat/plan-0003-workflow-standardization
```

Phase branches:

```text
feat/plan-0003-ph01-planning-docs-and-naming
feat/plan-0003-ph02-phase-lifecycle-and-status
feat/plan-0003-ph03-low-level-tool-refinement
feat/plan-0003-ph04-output-and-memory-surface
feat/plan-0003-ph05-docs-tests-and-skills
```

Each phase branch should be reviewed and merged back into:

```text
feat/plan-0003-workflow-standardization
```

The plan branch should eventually be merged into the user-selected target branch.

## Overall acceptance criteria

The plan is complete when:

1. Active implementation plans live under `docs/plans/<plan_key>/implementation-phases.md`.
2. Historical handoff/implementation docs are archived under `docs/archive/`.
3. Plan, phase, and task naming conventions are documented and used by skills.
4. Explicit plan, phase, and task keys exist where needed.
5. `.engram/task-plans/.../task-plan.md` is the standard per-task planning path.
6. Phase status supports `review_pending`.
7. Starting the first task in a planned phase moves the phase to `active`.
8. Finishing the last task in an active phase moves the phase to `review_pending`.
9. Phase review completion moves a phase from `review_pending` to `done`.
10. `engram_workflow_status` returns the current workflow state for all skills.
11. `engram_workflow_start` derives phase branch names from explicit plan/phase keys.
12. Low-level task, phase, and memory tools have predictable arguments and compact outputs.
13. Startup/workflow output no longer exposes obsolete guardrail-heavy guidance.
14. Normal memory tools no longer expose advanced lifecycle fields by default.
15. `py_structure --changed` exists and is used by `engram_workflow_verify`.
16. Task decomposition skill allows one-task phases when appropriate.
17. README, USER_MANUAL, AGENTS template, and skill templates match the new workflow.
18. Relevant regression tests pass through `engram_workflow_verify`.

---

# PH01: Planning docs, archive structure, and naming conventions

```yaml
phase_key: ph01-planning-docs-and-naming
phase_title: "[PLAN-0003 PH01] Planning docs, archive structure, and naming conventions"
branch: feat/plan-0003-ph01-planning-docs-and-naming
```

## Purpose

Standardize where active implementation plans live, where historical docs live, and how plan/phase/task keys are named.

This phase also prevents confusion between high-level implementation plans and per-task agent plans.

## Scope

- Add `docs/plans/plan-0003-workflow-standardization/implementation-phases.md`.
- Add or update `docs/adr/0003-workflow-standardization.md`.
- Create `docs/archive/` structure.
- Move/archive old root-level `docs/CODEX_*` workflow docs.
- Define deterministic plan/phase/task key conventions.
- Define `.engram/task-plans/.../task-plan.md` as the per-task plan path.
- Update relevant skill templates to reference `task-plan.md`.

## Suggested tasks

### T01: Create numbered planning docs structure

```yaml
task_key: t01-create-numbered-planning-docs-structure
title: "[PLAN-0003 PH01 T01] Create numbered planning docs structure"
```

Acceptance:

- `docs/plans/plan-0003-workflow-standardization/implementation-phases.md` exists.
- `docs/adr/0003-workflow-standardization.md` exists.
- Active plan docs are no longer expected at root-level `docs/CODEX_*` paths.

### T02: Archive historical workflow docs

```yaml
task_key: t02-archive-historical-workflow-docs
title: "[PLAN-0003 PH01 T02] Archive historical workflow docs"
```

Acceptance:

- Historical handoff/implementation docs are moved to `docs/archive/plan-0002-workflow-mvp-simplification/`.
- No active skill or README guidance points agents to archived files as the current source of truth.
- ADRs remain in `docs/adr/`.

### T03: Standardize naming and task-plan path guidance

```yaml
task_key: t03-standardize-naming-and-task-plan-paths
title: "[PLAN-0003 PH01 T03] Standardize naming and task-plan paths"
```

Acceptance:

- Plan key convention is documented.
- Phase key convention is documented.
- Task key convention is documented.
- Per-task plan path is documented as `.engram/task-plans/<plan_key>/<phase_key>/<task_key>/task-plan.md`.
- Skill templates use `task-plan.md`, not `implementation.md` or `implementation-plan.md`.

## Phase acceptance

- Documentation layout is unambiguous.
- Historical docs are not deleted unless clearly duplicate/noisy.
- Active plan source is `docs/plans/plan-0003-workflow-standardization/implementation-phases.md`.
- Agent-facing planning terminology distinguishes:
  - `implementation-phases.md` for full plan
  - `task-plan.md` for one task

---

# PH02: Phase lifecycle, workflow status, and branch naming

```yaml
phase_key: ph02-phase-lifecycle-and-status
phase_title: "[PLAN-0003 PH02] Phase lifecycle, workflow status, and branch naming"
branch: feat/plan-0003-ph02-phase-lifecycle-and-status
```

## Purpose

Make workflow state explicit and machine-readable. A skill should not need multiple exploratory tool calls to understand the current phase, review phase, active task, next task, next action, or expected phase branch.

## Scope

- Add explicit key support where needed:
  - `projects.plan_key`
  - `phases.key`
  - `tasks.key`
- Add `review_pending` phase status.
- Update phase validation, migrations, docs, and serializers.
- Auto-activate phase when first task starts.
- Auto-mark phase `review_pending` when last task finishes.
- Add `engram_workflow_status`.
- Update `engram_workflow_start` branch derivation.
- Update workflow start/finish outputs to expose phase status transitions and target branch clearly.

## Suggested tasks

### T01: Add explicit plan, phase, and task keys

```yaml
task_key: t01-add-explicit-plan-phase-task-keys
title: "[PLAN-0003 PH02 T01] Add explicit plan, phase, and task keys"
```

Acceptance:

- Data model supports explicit plan, phase, and task keys where needed.
- Keys are not parsed from display titles.
- Keys are included in relevant serializers and MCP outputs.
- Key uniqueness is enforced at the appropriate scope.
- Existing data is migrated or safely handled.

### T02: Add `review_pending` phase status

```yaml
task_key: t02-add-review-pending-phase-status
title: "[PLAN-0003 PH02 T02] Add review_pending phase status"
```

Acceptance:

- `review_pending` is accepted wherever phase statuses are validated.
- Existing phase statuses continue to work.
- User-facing display label is `To be reviewed`.
- Tests cover valid and invalid phase statuses.

### T03: Auto-update phase status during workflow start and finish

```yaml
task_key: t03-auto-update-phase-status-in-workflow
title: "[PLAN-0003 PH02 T03] Auto-update phase status in workflow start and finish"
```

Acceptance:

- Starting a task in a planned phase moves the phase to `active`.
- Finishing the last task in an active phase moves the phase to `review_pending`.
- Finishing a non-final task does not mark the phase `review_pending`.
- No unrelated phase is modified.

### T04: Add `engram_workflow_status`

```yaml
task_key: t04-add-workflow-status-tool
title: "[PLAN-0003 PH02 T04] Add engram_workflow_status"
```

Acceptance:

- Tool returns project, plan, active phase, review phase, active task, next task, counts, and next action.
- Tool works when there is no active phase.
- Tool works when there is a review-pending phase.
- Tool works when there is an active task.
- Tool output is compact and deterministic.
- Skills can use this as their first state lookup.

### T05: Update workflow branch naming

```yaml
task_key: t05-update-workflow-branch-naming
title: "[PLAN-0003 PH02 T05] Update workflow branch naming"
```

Acceptance:

- `engram_workflow_start` creates/checks out phase branches using the new convention.
- Branch names are derived from explicit plan and phase keys, not display titles.
- Phase branch format is:

  ```text
  feat/<plan_key>-<phase_key>
  ```

- Example:

  ```text
  feat/plan-0003-ph02-phase-lifecycle-and-status
  ```

- Missing plan or phase keys produce actionable errors for normal planned workflow tasks.
- Legacy/unphased fallback behavior is explicit if retained.
- Tests cover branch name derivation.

### T06: Update phase completion behavior

```yaml
task_key: t06-update-phase-completion-behavior
title: "[PLAN-0003 PH02 T06] Update phase completion behavior"
```

Acceptance:

- Phase completion is intended for `review_pending` phases.
- Completion moves phase to `done`.
- Error messages tell the user which unfinished tasks or review blockers remain.
- Phase review skill guidance matches the new lifecycle.

## Phase acceptance

- A skill can call one workflow status tool and know what to do next.
- Phase status lifecycle is `planned -> active -> review_pending -> done`.
- Workflow branch naming matches the plan/phase key convention.
- No `reviewed` terminal status exists.

---

# PH03: Low-level tool argument and output refinement

```yaml
phase_key: ph03-low-level-tool-refinement
phase_title: "[PLAN-0003 PH03] Low-level task, phase, and memory tool refinement"
branch: feat/plan-0003-ph03-low-level-tool-refinement
```

## Purpose

Make low-level tools useful for skills, not just humans. Tools should return precise, compact, filtered state so agents do not need repeated calls to infer current workflow context.

## Scope

- Refine `engram_task_list`.
- Refine task get/create/create_many/update outputs where needed.
- Refine `engram_phase_list`.
- Refine phase get/start/complete/update outputs where needed.
- Refine `engram_memory_list`.
- Optionally align `engram_memory_search` with list behavior or document its specific use.
- Standardize `ok`, `filters`, `count`, `items`, and `next_action` output patterns.

## Suggested tasks

### T01: Refine task tool filters and compact output

```yaml
task_key: t01-refine-task-tool-output
title: "[PLAN-0003 PH03 T01] Refine task tool filters and compact output"
```

Recommended `engram_task_list` arguments:

```text
status: open | in_progress | blocked | done | cancelled | all
phase_ref: string | null
scope: current | review_pending | all
view: compact | detail
```

Acceptance:

- Default task list behavior is useful in the current workflow context.
- Output includes resolved filters.
- Output includes task key, phase id, phase key, phase title, and `is_verified`.
- Output avoids unnecessary full descriptions in compact mode.
- Tests cover current, review_pending, and all scopes.

### T02: Refine phase tool filters and compact output

```yaml
task_key: t02-refine-phase-tool-output
title: "[PLAN-0003 PH03 T02] Refine phase tool filters and compact output"
```

Recommended `engram_phase_list` arguments:

```text
status: planned | active | review_pending | done | blocked | cancelled | all
view: compact | detail
```

Acceptance:

- Output marks `current`, `review_candidate`, and `next_planned`.
- Output includes phase key/title/status consistently.
- Output helps agents choose the next phase without extra calls.

### T03: Refine memory tool output and query behavior

```yaml
task_key: t03-refine-memory-tool-output
title: "[PLAN-0003 PH03 T03] Refine memory tool output and query behavior"
```

Recommended `engram_memory_list` arguments:

```text
query: string | null
limit: int
view: compact | detail
```

Acceptance:

- Compact memory output avoids lifecycle noise.
- Query behavior is documented.
- Normal output does not expose tags, levels, demotion, supersession, always_include, scope, or memory type unless explicitly in an internal/debug view.

### T04: Standardize tool response envelope

```yaml
task_key: t04-standardize-tool-response-envelope
title: "[PLAN-0003 PH03 T04] Standardize low-level tool response envelope"
```

Acceptance:

- List tools return `ok`, `filters`, `count`, `items`, and `next_action`.
- Error responses are concise and actionable.
- Output shape is documented for skill authors.

## Phase acceptance

- Task decomposition and phase review skills can inspect state without repeated exploratory list calls.
- Tool outputs are compact by default.
- Detailed output remains available when needed.

---

# PH04: Agent-facing output simplification and memory surface cleanup

```yaml
phase_key: ph04-output-and-memory-surface
phase_title: "[PLAN-0003 PH04] Agent-facing output simplification and memory surface cleanup"
branch: feat/plan-0003-ph04-output-and-memory-surface
```

## Purpose

Remove outdated or noisy content from agent-facing workflow outputs and simplify memory tools so the normal agent interface matches the MVP design.

## Scope

- Simplify `engram_workflow_start` output.
- Remove obsolete guardrail-heavy sections from startup/work-order text.
- Keep only task-relevant context, acceptance, files, verification, task-plan path, and next steps.
- Hide or unregister advanced memory lifecycle tools from the normal MCP surface.
- Keep memory CRUD and batch update/delete.
- Ensure README/User Manual/tool docs match actual exposed tools.

## Suggested tasks

### T01: Simplify workflow start output

```yaml
task_key: t01-simplify-workflow-start-output
title: "[PLAN-0003 PH04 T01] Simplify workflow start output"
```

Acceptance:

- Start output emphasizes current task, objective, acceptance, relevant files, verification, and required task-plan path.
- Obsolete project guardrail-heavy sections are removed.
- Output tells the agent to write `.engram/task-plans/.../task-plan.md` for non-trivial tasks.
- Output includes the resolved target branch.

### T02: Simplify normal memory MCP surface

```yaml
task_key: t02-simplify-memory-mcp-surface
title: "[PLAN-0003 PH04 T02] Simplify normal memory MCP surface"
```

Acceptance:

- Normal agent-facing memory tools expose CRUD plus batch update/delete.
- Advanced lifecycle operations are removed from normal registration or gated behind an internal/debug surface.
- Normal memory outputs hide legacy lifecycle fields.

### T03: Align workflow guidance with new current-state and phase status

```yaml
task_key: t03-align-workflow-guidance
title: "[PLAN-0003 PH04 T03] Align workflow guidance with workflow status and review_pending"
```

Acceptance:

- Finish output clearly reports whether a commit was created.
- No-op finish behavior remains allowed but explicit.
- Finish output clearly reports when a phase moved to `review_pending`.
- Guidance instructs the user/agent to use the phase review skill for review-pending phases.

## Phase acceptance

- Agent-facing workflow output is short, direct, and task-focused.
- Memory tools match the simplified MVP interface.
- No-op finish behavior is explicit, not misleading.

---

# PH05: Regression tests, documentation, and skill template updates

```yaml
phase_key: ph05-docs-tests-and-skills
phase_title: "[PLAN-0003 PH05] Regression tests, documentation, and skill template updates"
branch: feat/plan-0003-ph05-docs-tests-and-skills
```

## Purpose

Lock the new workflow behavior into tests and update public/internal documentation so future agents follow the same conventions.

## Scope

- Add `py_structure --changed`.
- Update `engram_workflow_verify` to use `py_structure --changed`.
- Update tests for key fields, branch naming, phase lifecycle, workflow status, tool output shapes, memory surface, and docs assumptions.
- Update task decomposition skill.
- Update start task skill.
- Update phase review skill.
- Update README and USER_MANUAL.
- Remove/archive outdated `docs/skills/` content.

## Suggested tasks

### T01: Add `py_structure --changed`

```yaml
task_key: t01-add-py-structure-changed-mode
title: "[PLAN-0003 PH05 T01] Add py_structure --changed mode"
```

Acceptance:

- Default `py_structure` remains staged-only.
- `py_structure --changed` checks staged, unstaged modified, and untracked Python files.
- `engram_workflow_verify` uses `--changed`.
- Tests cover staged-only and changed modes.

### T02: Update skill templates

```yaml
task_key: t02-update-skill-templates
title: "[PLAN-0003 PH05 T02] Update Engram skill templates"
```

Acceptance:

- All skills start by calling `engram_workflow_status`.
- Task decomposition skill allows one-task phases.
- Task decomposition skill uses deterministic naming.
- Start task skill uses `.engram/task-plans/.../task-plan.md`.
- Phase review skill uses `review_pending` phases.
- Phase review skill asks which target branch to merge into, never assumes `main`.

### T03: Update README and user manual

```yaml
task_key: t03-update-readme-and-user-manual
title: "[PLAN-0003 PH05 T03] Update README and USER_MANUAL"
```

Acceptance:

- Docs describe current tool surface accurately.
- Docs describe phase lifecycle accurately.
- Docs describe planning file structure accurately.
- Docs describe branch naming accurately.
- Docs do not point to archived docs as active guidance.

### T04: Add regression coverage for plan 0003 behavior

```yaml
task_key: t04-add-regression-tests
title: "[PLAN-0003 PH05 T04] Add regression coverage for workflow standardization"
```

Acceptance:

- Tests cover explicit keys.
- Tests cover branch name derivation.
- Tests cover `review_pending`.
- Tests cover workflow status output.
- Tests cover low-level tool compact outputs.
- Tests cover memory surface simplification.
- Tests cover task-plan path guidance.
- Existing workflow verify/finish tests still pass.

## Phase acceptance

- Documentation, skills, tests, and implementation agree.
- `engram_workflow_verify` remains the only verification gate.
- No verify profiles or extra verify tools are introduced.
- Task decomposition does not create unnecessary tasks.

---

# Task decomposition rules to add to skill template

Add this section to `agent-files/skills/engram-task-decomposition-template.md`:

```md
## Task sizing rules

Create the fewest tasks necessary to complete the selected phase safely.

A phase may have exactly one task when:
- the work is cohesive
- the affected files are limited
- the acceptance criteria can be verified together
- one Codex implementation session can complete it without losing context

Split into multiple tasks only when at least one is true:
- separate user-visible behaviors are being changed
- separate subsystems are affected
- separate verification gates are useful
- the task would require too many files or too much context
- a partial implementation would be useful to review independently

Do not create multiple tasks only because a phase should “look balanced.”
```

Add this naming section:

```md
## Naming convention

Use deterministic keys.

Plan key:
`plan-0003-workflow-standardization`

Phase key:
`ph01-planning-docs-and-naming`

Task key:
`t01-update-doc-structure`

Task title format:
`[PLAN-0003 PH01 T01] Update docs plan structure`

Task plan path:
`.engram/task-plans/<plan_key>/<phase_key>/<task_key>/task-plan.md`
```

---

# Verification

For each implementation task, use:

```text
engram_workflow_verify
```

Do not introduce verify profiles in this plan.

The verify command sequence should continue to be simple, with the only correctness change being:

```bash
uv run python -m engram.hooks.py_structure --changed
```

---

# Final plan review checklist

Before implementing this plan, confirm:

- PH01 includes all directory reorganization.
- PH02 includes explicit keys, phase lifecycle, workflow status, and branch naming.
- PH03 is focused on low-level tool usability.
- PH04 is focused on agent-facing output and memory simplification.
- PH05 is focused on tests, docs, skills, and `py_structure --changed`.
- No phase is too broad.
- No phase exists only for a tiny mechanical change.
