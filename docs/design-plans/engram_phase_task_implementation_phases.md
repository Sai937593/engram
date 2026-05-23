# Engram Phase-Task Hierarchy Implementation Phase Plan

## Goal

Implement first-class phases before memory retrieval changes.

The intended final structure is:

```text
Project
  -> Phase
       -> Task
```

This plan is intentionally phase-level. It is meant to be split into concrete Engram tasks later.

Tests should be added inside each implementation phase, not deferred to the end. The final hardening phase is for coverage gaps, docs, and cross-command regression checks.

## Phase 1 - Schema, Domain Model, and Legacy Migration

### Objective

Add first-class phase storage, task-to-phase association, and a compatibility layer for existing `task.phase` data.

### Work Items

```text
- Add `phases` table.
- Add nullable `phase_id` to tasks.
- Define phase statuses.
- Add phase model/domain object.
- Add effective phase-title helper that prefers Phase.title and falls back to legacy task.phase.
- Create phases from distinct legacy task.phase values per project.
- Backfill task.phase_id from legacy task.phase.
- Preserve existing task behavior.
- Add schema and migration tests.
```

### Expected Outcome

Engram can store project phases independently from tasks while existing databases and workflows continue to work.

### Acceptance Criteria

```text
- A project can have multiple phases.
- A task can reference a phase.
- Existing tasks without phase_id still work.
- Existing tasks with legacy task.phase are backfilled to phase_id.
- Migration is idempotent.
- Duplicate legacy phase strings map to one phase per project.
- Empty/null legacy phase strings are handled safely.
- No existing task commands break.
- Branch naming and commit scopes can still derive a stable phase label.
```

---

## Phase 2 - Phase CRUD CLI

### Objective

Expose phase management through CLI commands.

### Work Items

```text
- Add `engram phase add`.
- Add `engram phase list`.
- Add `engram phase get`.
- Add `engram phase update`.
- Add `engram phase start`.
- Add `engram phase done`.
- Register phase commands in the CLI.
- Add phase command tests.
```

### Expected Outcome

Users and agents can create, inspect, activate, update, and complete phases.

### Acceptance Criteria

```text
- Phase commands work from a registered project directory.
- Phase titles are unique per project after normalization, or ambiguous names are rejected.
- `phase start` makes exactly one phase active for the project.
- `phase start` handles any previously active phase deterministically.
- `phase done` records evidence.
- `phase done` rejects incomplete phases by default when active tasks remain.
- `phase done --force` can complete a phase with remaining tasks if that option is implemented.
- Phase list is ordered by order_index.
- order_index defaults to max(project order_index) + 1.
```

---

## Phase 3 - Task Integration

### Objective

Allow tasks to belong to phases and make task listing phase-aware.

### Work Items

```text
- Support `engram task add --phase`.
- Resolve `--phase` by id or unique title.
- Support `engram task list --phase`.
- Support updating task phase association.
- Display phase information in task get/list where useful.
- Keep legacy `phase` field readable during compatibility.
- Add task-phase integration tests.
```

### Expected Outcome

Tasks can be grouped under phases in normal workflows.

### Acceptance Criteria

```text
- New tasks can be created under a phase.
- Tasks can be filtered by phase.
- Task details show associated phase using the effective phase title.
- Ambiguous phase names fail with a clear error.
- Existing task commands remain backward compatible.
```

---

## Phase 4 - Workflow Compatibility: Branches and Finish

### Objective

Move workflow behavior from legacy `task.phase` strings to first-class phases without changing user-visible semantics unexpectedly.

### Work Items

```text
- Update branch naming to use the effective phase title.
- Update finish commit scope to use the effective phase title.
- Update phase-complete detection to use phase_id where available.
- Preserve fallback behavior for tasks without phase_id.
- Add start/finish compatibility regression tests.
```

### Expected Outcome

The two-command workflow continues to behave the same for users while using first-class phase data internally.

### Acceptance Criteria

```text
- Existing legacy tasks still check out the same expected phase branch.
- New phase-linked tasks check out the branch derived from Phase.title.
- `engram finish` uses a stable conventional commit scope.
- Phase-complete messaging works for phase_id tasks.
- Tasks without a phase still use misc fallback behavior.
```

---

## Phase 5 - Phase-Aware `engram start`

### Objective

Make `engram start` use the active phase when selecting work.

### Work Items

```text
- Resolve the active phase for current project.
- Prefer in-progress tasks inside the active phase.
- Prefer actionable todo tasks inside the active phase.
- Fall back to project-level task selection if no active phase exists.
- Include compact phase frame in start output.
- Add start-selection tests.
```

### Expected Outcome

`engram start` becomes phase-aware without changing memory retrieval yet.

### Acceptance Criteria

```text
- If an active phase exists, `engram start` selects from that phase first.
- If no active phase exists, existing behavior still works.
- Output includes current phase title/status/goal if available.
- Task state mutation behavior remains consistent with current `start`.
- Dirty-working-tree safety still uses the selected task's target branch.
```

---

## Phase 6 - Phase Context Formatting

### Objective

Make phase context useful but compact.

### Work Items

```text
- Add compact phase summary builder.
- Include phase goal and acceptance summary.
- Avoid dumping long phase evidence by default.
- Add optional full/details behavior later if needed.
- Add formatting tests.
```

### Expected Outcome

`engram start` gives the agent useful phase-level situational awareness.

### Acceptance Criteria

```text
- Phase context is short and readable.
- Long descriptions/evidence are summarized or truncated.
- Output remains stable and predictable.
- Output remains ASCII-safe unless the surrounding command output intentionally uses Unicode.
```

---

## Phase 7 - Documentation and Final Hardening

### Objective

Harden the phase-task model before memory retrieval work starts.

### Work Items

```text
- Review schema migration tests for edge cases.
- Review phase command tests.
- Review task-phase integration tests.
- Review start-selection tests.
- Add any missing regression tests.
- Update README/manual command references.
- Document compatibility/deprecation behavior for legacy task.phase.
```

### Expected Outcome

The phase-task backbone is reliable enough to support later retrieval features.

### Acceptance Criteria

```text
- Existing tests pass.
- New phase workflows are covered.
- Migration is covered.
- Documentation reflects Project -> Phase -> Task structure.
- Legacy task.phase deprecation path is documented.
```

## Out of Scope for This Plan

Do not include:

```text
- semantic search
- FTS retrieval changes
- memory hierarchy implementation
- context budget redesign
- embedding index
- rank fusion
- phase memory scope
```

These belong to the separate memory retrieval/start-context plan.
