# Codex Handoff: Engram Workflow Redesign

## Purpose

Redesign Engram around a tighter agent workflow: repo-local project state, MCP-first operation, phase intake, task decomposition, gated task execution, verification, memory hygiene, branch-aware skills, and clean Markdown MCP outputs.

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

## Decision Locks

Do not change these without user approval:

- Keep the primary execution loop as `workflow_start -> workflow_verify -> memory review -> workflow_finish`.
- Use repo-local `.engram/memory.db` as the only normal project state store.
- Do not keep global DB as primary project storage.
- Do not rely on repo-path binding in a global DB for project resolution.
- Make Engram MCP-first; normal agent workflows must not depend on CLI commands.
- Do not introduce new workflow functionality only in CLI.
- Keep Python + uv packaging/runtime; do not rewrite Engram in Node/npm for this redesign.
- Do not add Project Card as a new abstraction in this redesign.
- Do not force memory creation for every task; force memory review only.
- Do not make CRUD/lifecycle tools the main agent workflow path.
- Do not auto-start the next task from `workflow_finish`.
- Do not assume `main` is always the integration branch.
- Skills and workflow guidance must respect the current/base branch for the active redesign session.
- Keep detailed reasoning in skills; keep tool outputs compact.

---

## Branch Policy

Engram skills and workflow guidance should be branch-aware.

For this redesign, Codex should treat the active redesign branch as the integration/base branch, not `main`.

Expected behavior:

- Detect or respect the current branch/base branch for the active session.
- Create phase/task branches from the active redesign/base branch.
- Merge or target completed phase/task work back to the active redesign/base branch.
- Do not merge, rebase, or open PRs into `main` unless the user explicitly asks.
- Update skill-bank instructions so agents do not hardcode `main` as the default merge target.

This should be handled early in the redesign so the user does not need to repeat branch instructions manually.

---

## Storage and MCP Integration

Engram should use repo-local project state only.

Target shape:

```text
project-root/
  .engram/
    memory.db
    config.toml
```

Expected behavior:

- MCP server is configured once in the client/machine.
- Per project, Engram initializes `.engram/memory.db` once.
- MCP tools resolve the active project from the current repo/workspace, not from a global project registry.
- `.engram/` should be added to `.gitignore` during project initialization.
- Missing repo-local state should produce a clear `not initialized` response with the next MCP action.

Do not require per-project MCP command changes. The same MCP command should work across projects when launched from the project workspace.

---

## MCP-First Product Surface

All normal functionality needed by Codex should exist in services and MCP tools/resources.

CLI commands should not be required for:

- project initialization
- project status/current project lookup
- task/phase/memory lifecycle operations
- workflow start/verify/finish
- memory review recording
- diagnostics needed by agents

Any existing CLI-only behavior should be migrated into service-layer functions and exposed through MCP.

A tiny CLI may remain temporarily for human diagnostics or migration, but it must not be the main product/workflow path.

---

## Packaging Decision

Keep Engram as a Python project managed with uv.

Target runtime model:

```text
Python implementation
uv packaging/runtime
STDIO MCP server
repo-local `.engram/memory.db`
MCP-first workflow
```

Do not rewrite Engram in Node/npm for MCP integration. MCP reliability should be achieved through deterministic server startup, stable schemas, repo-local DB discovery, compact outputs, and clear errors.

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

## Skills to Add or Refine

### Branch-Aware Skill Guidance

Purpose:

Prevent skills from assuming `main` as the merge/integration target.

Skills should instruct agents to:

- respect the current active branch/base branch
- avoid touching `main` unless user-approved
- target merges/PRs to the active redesign/base branch during long-running redesign work

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

### Project/admin lifecycle

Needed MCP actions:

- project init
- current project
- project status / diagnostics
- update project metadata if needed

Do not use global project listing/binding as the normal model.

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

---

## Target New-Project Session

```text
Open Codex in repo
  -> MCP server starts with same command as other projects
  -> Engram detects missing `.engram/memory.db`
  -> Codex calls project init MCP tool
  -> Engram creates repo-local DB and project metadata
  -> Engram adds `.engram/` to `.gitignore`
  -> Codex can use workflow tools normally
```

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
- keeping global DB as normal project storage
- requiring CLI for normal agent workflows
- rewriting the project in Node/npm
- hardcoding `main` as the integration branch in skills or workflow guidance

---

## Acceptance Criteria

This redesign is successful when:

- project state is repo-local under `.engram/memory.db`
- MCP can initialize and use a new repo without per-project MCP command changes
- normal Codex workflows do not require CLI commands
- Python + uv remain the packaging/runtime model
- skills and workflow guidance respect the current/base branch instead of assuming `main`
- `workflow_start` returns a compact, non-duplicative Work Order
- `workflow_verify` exists and gates finish
- `workflow_finish` blocks when verification or memory review is missing
- task decomposition creates complete task metadata
- incomplete tasks cannot be started
- memory freshness is actively reviewed before finish
- guardrails remain the primary durable project context abstraction
- workflow outputs guide agents without bloating context
- Codex can execute one task at a time without scanning the whole codebase unnecessarily
