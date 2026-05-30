# Codex Handoff: Engram Workflow Redesign

## Purpose

Redesign Engram around a tighter agent workflow: phase intake, task decomposition, gated task execution, verification, memory hygiene, and clean Markdown MCP outputs.

This handoff defines **what to build/refine**. Implementation details should be decided during the build phase.

---

## Core Direction

Engram should act as a local workflow governor for coding agents.

Primary model:

```text
Planning doc -> phase intake -> task decomposition -> draft tasks -> task quality gate -> ready tasks

ready task -> workflow_start -> implementation -> workflow_verify -> memory review -> workflow_finish
```

The main workflow should use a small number of strong tools and gates instead of many loose hints.

---

## Primary Workflow Tools

### 1. `engram_workflow_start`

Refine this into a compact **Work Order** generator.

Output should include:

- task objective
- acceptance criteria
- relevant files / search hints
- applicable guardrails
- relevant task memories
- boundaries / out-of-scope
- required gates
- exactly one next action

Avoid:

- duplicated task/phase metadata
- YAML-style database dumps
- generic hints
- auto-continuation instructions

---

### 2. `engram_workflow_verify`

Add this as a required verification gate before finish.

Purpose:

- run local quality checks
- summarize pass/fail status
- identify first fix target
- prevent finish when checks are missing or stale

Output should be short and action-oriented.

---

### 3. `engram_workflow_finish`

Refine this into a gated finish action.

It should block unless:

- task is active / finishable
- verification passed
- verification is not stale
- memory review outcome has been recorded

Finish output should stop after task completion.

Do not tell the agent to immediately start another task.

---

## Required Gates

### Task Readiness Gate

Only ready tasks should be selectable by `workflow_start`.

A task should not become ready unless it has:

- clear objective / description
- acceptance criteria
- relevant files or search hints
- verification expectation
- dependencies if applicable
- scope boundaries / out-of-scope if applicable

### Verification Gate

`workflow_finish` should be blocked unless `workflow_verify` passed after the latest relevant changes.

### Memory Review Gate

`workflow_finish` should be blocked unless a memory review outcome has been recorded.

The outcome may be:

- memory created
- memory superseded
- memory demoted
- memory archived
- memory deleted
- no memory change needed

Do not force memory creation on every task. Force memory review.

---

## Skills to Add

### Task Decomposition Skill

Purpose:

Convert a supplied implementation phase document into high-quality Engram tasks.

The skill should guide the agent to create tasks with:

- title
- objective / description
- acceptance criteria
- relevant files
- search hints
- dependencies
- verification guidance
- out-of-scope boundaries
- risk notes if needed

This prevents agents from creating weak tasks with only title/description/dependency.

### Memory Review Skill

Purpose:

Guide the agent after verification and before finish.

The skill should help the agent decide whether to:

- create durable new memory
- supersede stale memory
- demote stale guardrails
- archive obsolete memory
- delete wrong/duplicate/harmful memory
- record no memory change

Keep detailed memory-review reasoning in the skill, not in large tool outputs.

---

## MCP Output Refinements

All primary workflow outputs should be Markdown-first.

Rules:

- one fact appears once
- no repeated phase/task/status blocks
- exactly one `Next action` section
- dense bullets over prose
- no large YAML/JSON-style dumps in the visible text
- state-aware guidance instead of generic hints

Recommended section style:

```md
# Work Order

Status: ready
Task: `<id>` — <title>
Phase: <phase>
Branch: `<branch>`

## Objective
...

## Acceptance
...

## Start here
- `path/to/file.py` — reason

## Guardrails
- ...

## Relevant memory
- ...

## Boundaries
- ...

## Required gates
- ...

## Next action
...
```

---

## Memory and Guardrails

Do not add a new Project Card abstraction now.

Use the existing concepts:

- project summary
- guardrails
- L0/L1 memories
- always-include memories
- task memory candidates
- startup context

`workflow_start` should include guardrails and task-relevant memories in compact form.

Memory search output should also be refined to Markdown and made more useful when no results are found.

---

## Lifecycle / CRUD Coverage

Add or refine lifecycle tools for core entities.

### Task lifecycle

Needed actions:

- create draft
- validate
- mark ready
- update
- block
- unblock
- cancel
- archive/delete

### Memory lifecycle

Needed actions:

- search
- get
- create
- update
- supersede
- demote
- archive
- delete

Prefer supersede/archive/demote over delete unless the memory is wrong, duplicate, harmful, or accidental.

### Phase lifecycle

Needed actions:

- create
- update
- start
- complete
- cancel
- archive

### Project/admin lifecycle

Keep this lighter for now.

Needed actions:

- current project
- update project metadata if needed
- inspect bound repo context

---

## Target Phase-Splitting Session

```text
User provides implementation phase doc
  -> Codex reads phase doc
  -> Codex applies task decomposition skill
  -> Codex creates draft tasks
  -> Engram validates task quality
  -> Codex fixes invalid task metadata
  -> tasks become ready
  -> workflow_start can select first ready task
```

---

## Target Task Session

```text
workflow_start
  -> Work Order returned
  -> Codex inspects relevant files first
  -> Codex implements scoped change
  -> workflow_verify
  -> Codex fixes failures
  -> Memory Review Skill
  -> memory review outcome recorded
  -> workflow_finish
  -> stop unless user asks to continue
```

---

## Non-Goals for This Redesign

Do not prioritize:

- adding Project Card as a new abstraction
- making tool outputs large instruction manuals
- forcing memory creation for every task
- letting CRUD tools become the main workflow path
- auto-starting the next task after finish
- exposing raw database writes to agents

---

## Acceptance Criteria

This redesign is successful when:

- `workflow_start` returns a compact, non-duplicative Work Order
- `workflow_verify` exists and gates finish
- `workflow_finish` blocks when verification or memory review is missing
- task decomposition creates complete task metadata
- incomplete tasks cannot be started
- memory freshness is actively reviewed before finish
- guardrails remain the primary durable project context abstraction
- workflow outputs guide agents without bloating context
- Codex can execute one task at a time without scanning the whole codebase unnecessarily
