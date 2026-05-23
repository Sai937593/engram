# Engram Phase–Task Hierarchy Design Spec

## 1. Purpose

This design promotes `phase` from a loose task metadata field into a first-class planning/state entity.

The goal is to make Engram's project workflow more structured:

```text
Project
  └── Phase
        └── Task
```

This should be implemented before the memory retrieval redesign, because retrieval and startup context will benefit from having a clear active phase and task structure.

## 2. Design Decision

Use a first-class `Phase` entity.

Do not model phases as tasks.
Do not keep phase only as a free-form task string long-term.
Do not introduce separate phase-memory scope initially.

## 3. Entity Model

### Project

Represents a repository/project registered in Engram.

Conceptual fields:

```text
id
name
summary
status
created_at
updated_at
```

### Phase

Represents a meaningful project stage or milestone.

Conceptual fields:

```text
id
project_id
title
description
status
order_index
acceptance
evidence
created_at
updated_at
```

Recommended phase statuses:

```text
planned
active
done
blocked
cancelled
```

Only one phase should usually be active per project, but the system does not need to enforce this strictly in the first version unless implementation is simple.

### Task

Represents an executable unit of work.

Conceptual fields:

```text
id
project_id
phase_id
title
description
status
priority
acceptance
evidence
depends_on
created_at
updated_at
```

Recommended task statuses remain:

```text
todo
in-progress
done
blocked
cancelled
```

## 4. Relationship Rules

```text
A project has many phases.
A phase has many tasks.
A task belongs to one phase.
A task may temporarily have no phase during migration/backward compatibility.
```

Preferred future invariant:

```text
Every non-archived task belongs to a phase.
```

## 5. Phase Responsibilities

A phase should represent:

```text
- project stage
- milestone
- planning boundary
- group of related tasks
- high-level goal and acceptance criteria
```

A phase should not represent:

```text
- an individual implementation task
- a memory category
- a substitute for project-level constraints
```

## 6. Task Responsibilities

A task should represent:

```text
- specific work item
- implementation/research/design unit
- testable acceptance criteria
- progress/evidence log
```

Tasks remain the unit of execution.

## 7. Memory Scope Decision

Do not add `phase` as a memory scope initially.

Supported memory scopes should remain:

```text
project
task
```

Rationale:

```text
Project memories = durable project-wide knowledge.
Task memories = reusable work-derived knowledge.
Phase = planning/state container, not a memory plane.
```

Phase-level context should live in the phase entity itself:

```text
title
description
acceptance
evidence/notes
status
```

Optional provenance fields can be added later:

```text
source_phase_id
source_task_id
```

This allows a memory to be created during a phase without becoming a separate “phase memory.”

## 8. Startup Context Impact

`engram start` should eventually include:

```text
1. Project frame
2. Current active phase
3. Current/next task in that phase
4. Relevant memory pack
5. Next action
```

For the phase-task implementation itself, memory retrieval does not need to be changed yet.

Example future output:

```text
Project:
Engram — local-first memory system for coding agents.

Current phase:
Startup context redesign
Goal: Make `engram start` produce useful project + task context without bloating output.

Current task:
Implement first-class phases and migrate task.phase strings to phase_id.
```

## 9. CLI Design

Recommended new commands:

```bash
engram phase add "<title>" [--description TEXT] [--status planned|active|done|blocked|cancelled] [--acceptance TEXT]
engram phase list [--all]
engram phase get <phase_id>
engram phase start <phase_id>
engram phase done <phase_id> --evidence "<proof>"
engram phase update <phase_id> --field <field> --value <value>
```

Task commands should support phase association:

```bash
engram task add "<title>" --phase <phase_id_or_name>
engram task list --phase <phase_id_or_name>
engram task update <task_id> --field phase_id --value <phase_id>
```

Existing task behavior should remain backward compatible during migration.

## 10. `engram start` Behavior

Initial phase-aware behavior:

```text
1. Resolve current project.
2. Find active phase.
3. If active phase exists, select next actionable task from that phase.
4. If no active phase exists, fall back to existing task-next behavior.
5. Mark selected task as in-progress if `start` currently mutates task state.
6. Print compact phase + task context.
```

Selection priority:

```text
active phase tasks first
then project-level actionable tasks without phase
then existing global task next behavior
```

## 11. Migration Strategy

Existing tasks may already have a `phase` string field.

Migration plan:

```text
1. Create phases table.
2. Read distinct non-empty task.phase values.
3. Create one phase per distinct phase string per project.
4. Backfill task.phase_id based on old task.phase.
5. Keep old task.phase temporarily for compatibility.
6. Mark old task.phase as deprecated.
7. Later remove or ignore old task.phase after commands fully use phase_id.
```

## 12. Non-Goals

This phase-task redesign should not include:

```text
- semantic memory retrieval
- embedding models
- vector storage
- rank fusion
- phase-memory scope
- complex dependency graph between phases
- multi-project roadmap management
```

## 13. Success Criteria

The design is successful if:

```text
- phases are first-class entities
- tasks can be grouped under phases
- `engram start` can prefer tasks from the active phase
- old task phase metadata can be migrated safely
- the model remains simple enough for CLI usage
- future memory retrieval can use project + phase + task context cleanly
```
