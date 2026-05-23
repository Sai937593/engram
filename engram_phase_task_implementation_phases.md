# Engram Phase–Task Hierarchy Implementation Phase Plan

## Goal

Implement first-class phases before memory retrieval changes.

The intended final structure is:

```text
Project
  └── Phase
        └── Task
```

This plan is intentionally phase-level. It is meant to be split into concrete Codex tasks later.

## Phase 1 — Schema and Domain Model

### Objective

Add first-class phase storage and task-to-phase association.

### Work Items

```text
- Add `phases` table.
- Add `phase_id` to tasks.
- Define phase statuses.
- Add phase model/domain object.
- Preserve existing task behavior.
```

### Expected Outcome

Engram can store project phases independently from tasks.

### Acceptance Criteria

```text
- A project can have multiple phases.
- A task can reference a phase.
- Existing tasks without phase_id still work.
- No existing task commands break.
```

---

## Phase 2 — Phase CRUD CLI

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
```

### Expected Outcome

Users and agents can create, inspect, activate, update, and complete phases.

### Acceptance Criteria

```text
- Phase commands work from a registered project directory.
- `phase start` can mark a phase active.
- `phase done` records evidence.
- Phase list is ordered by order_index/status.
```

---

## Phase 3 — Task Integration

### Objective

Allow tasks to belong to phases and make task listing phase-aware.

### Work Items

```text
- Support `engram task add --phase`.
- Support `engram task list --phase`.
- Support updating task phase association.
- Display phase information in task get/list where useful.
```

### Expected Outcome

Tasks can be grouped under phases in normal workflows.

### Acceptance Criteria

```text
- New tasks can be created under a phase.
- Tasks can be filtered by phase.
- Task details show associated phase.
- Task commands remain backward compatible.
```

---

## Phase 4 — Migration from Old Task Phase Metadata

### Objective

Convert existing task `phase` string metadata into first-class phases.

### Work Items

```text
- Detect distinct old task.phase values per project.
- Create phase records for those values.
- Backfill task.phase_id.
- Keep old phase field readable during compatibility period.
- Add migration tests.
```

### Expected Outcome

Existing Engram databases preserve phase information after migration.

### Acceptance Criteria

```text
- No task loses old phase information.
- Duplicate phase strings map to one phase per project.
- Empty/null phase strings are handled safely.
- Migration can run idempotently.
```

---

## Phase 5 — Phase-Aware `engram start`

### Objective

Make `engram start` use the active phase when selecting work.

### Work Items

```text
- Resolve active phase for current project.
- Prefer actionable tasks inside active phase.
- Fall back to project-level task selection if no active phase exists.
- Include compact phase frame in start output.
```

### Expected Outcome

`engram start` becomes phase-aware without changing memory retrieval yet.

### Acceptance Criteria

```text
- If an active phase exists, `engram start` selects from that phase first.
- If no active phase exists, existing behavior still works.
- Output includes current phase title/status/goal if available.
- Task state mutation behavior remains consistent with current `start`.
```

---

## Phase 6 — Phase Context Formatting

### Objective

Make phase context useful but compact.

### Work Items

```text
- Add compact phase summary builder.
- Include phase goal and acceptance summary.
- Avoid dumping long phase evidence by default.
- Add optional full/details behavior later if needed.
```

### Expected Outcome

`engram start` gives the agent useful phase-level situational awareness.

### Acceptance Criteria

```text
- Phase context is short and readable.
- Long descriptions/evidence are summarized or truncated.
- Output remains stable and predictable.
```

---

## Phase 7 — Tests and Documentation

### Objective

Harden the phase-task model before memory retrieval work starts.

### Work Items

```text
- Add schema migration tests.
- Add phase command tests.
- Add task-phase integration tests.
- Add start-selection tests.
- Update README/manual command references.
```

### Expected Outcome

The phase-task backbone is reliable enough to support later retrieval features.

### Acceptance Criteria

```text
- Existing tests pass.
- New phase workflows are covered.
- Migration is covered.
- Documentation reflects Project → Phase → Task structure.
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
