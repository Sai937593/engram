# Codex Handoff: CLI-First Engram MVP

## Goal

Refactor Engram from an MCP-first system into a CLI-first local workflow tool for agentic coding work.

The MVP should be small, functional, and usable. Avoid rebuilding broad MCP-era abstractions unless they are required by the CLI workflow.

## Primary Direction

Use the existing service layer as the application boundary.

Target shape:

```text
CLI commands
  -> service layer
  -> models / DB / Git helpers / artifact writer
```

The CLI should be a thin wrapper. Business behavior should live in services.

## MVP Product Definition

Engram MVP is a local-first CLI that provides:

- project initialization
- task and phase workflow state
- plain project memories
- always-included project tools
- task startup context
- local verification workflow
- commit/push workflow
- Markdown artifact history for every command

## Core Concepts

### Project

Represents one initialized repository/workspace.

### Phase

Groups related tasks. Keep existing phase behavior where practical, but simplify output and avoid adding new phase abstractions.

### Task

Represents executable work. Tasks should support basic status, priority, description, acceptance, dependency, evidence, and relevant files if already supported.

### Memory

Plain reusable project knowledge retrieved by relevance.

Remove MVP reliance on:

- memory type
- memory tags
- memory scope
- memory level
- guardrail demotion
- superseding
- always-include memory behavior

### Project Tool

Separate entity from memory.

Always shown in startup/task context. Used for project-specific commands, conventions, setup notes, and agent instructions.

### Command Artifact

Every Engram command writes a Markdown artifact under `.engram/artifacts/`.

The DB records artifact metadata, path, hash, status, and summary. The Markdown file remains the readable source of truth.

### Verification Run

Represents one local verification execution. Used by `commit` to confirm that the current task was verified before completion.

## Required CLI Workflow

### `start`

Responsibilities:

- resolve the current project
- select or resume the next actionable task
- prepare or switch to the task branch
- retrieve relevant memories
- include project tools
- write a startup Markdown artifact
- print concise terminal summary with artifact path

### `verify`

Responsibilities:

- resolve the current project and current task
- run configured verification checks
- record pass/fail state
- write a verification Markdown artifact
- print concise terminal summary with artifact path

Verification should be local and explicit. Do not rely on Git hooks for MVP behavior.

### `commit`

Responsibilities:

- resolve the current project and current in-progress task
- check for a successful recent verification record for the task/change set
- commit and push changes
- mark the task done only after successful commit/push
- write a commit Markdown artifact
- print concise terminal summary with artifact path

Do not combine `verify` and `commit` into one hidden workflow.

## Artifact Requirements

Every command should write an artifact, including small/read-only commands.

Artifact writer should be shared infrastructure, not per-command custom file handling.

Each artifact should have:

- command name
- status
- timestamp
- project ID
- task ID when relevant
- phase ID when relevant
- concise summary
- full Markdown body
- content hash stored in DB metadata

Avoid storing full Markdown bodies in the DB for MVP.

## Storage Requirements

Use a project-local ignored runtime directory:

```text
.engram/
  db/
  artifacts/
  inputs/
  templates/
```

Initialization should ensure `.engram/` is ignored by Git.

Do not create committed planning/output clutter in the repo root.

## Structured Input Policy

Use direct CLI args for simple commands.

Use YAML input files for commands with many fields or bulk updates.

Provide templates under `.engram/templates/` or packaged defaults that can be copied/generated into `.engram/inputs/`.

Do not overuse structured files for trivial commands.

## Simplification Rules

Remove or disable MCP-first behavior from the MVP path:

- MCP script entrypoint
- MCP optional dependency as product requirement
- MCP tools/resources
- MCP-specific docs/tests as active MVP expectations

Simplify memory behavior:

- no tags
- no levels
- no types
- no scopes
- no superseding
- no always-include memories
- no guardrail demotion

Project tools replace always-included memories.

## Testing Expectations

Add or update tests around:

- CLI wrappers call services correctly
- service behavior remains independent of CLI rendering
- every command writes artifact metadata and file body
- artifact DB records contain correct path/hash/status/summary
- simplified memory model accepts plain memories
- project tools are always included in startup context
- `verify` records verification runs
- `commit` refuses to complete an unverified task

Remove or rewrite tests that only validate MCP behavior.

## Documentation Updates

Update README and user manual to reflect CLI-first behavior.

Remove MCP-first positioning from MVP docs.

Document only high-level command responsibilities at this stage. Do not over-specify exact terminal or artifact output layout yet.

## Non-Goals

Do not implement:

- MCP compatibility layer
- artifact search
- artifact retention/pruning
- web UI
- full artifact body storage in DB
- complex memory audit taxonomy
- rich output format negotiation
- background workers
- remote services

## Success Criteria

The MVP is successful when a user can:

1. initialize a repo with Engram
2. create or load phases/tasks
3. run `start` to get task context and a saved artifact
4. complete implementation manually or through an agent
5. run `verify` to create a verification record/artifact
6. run `commit` to commit, push, mark task done, and create a commit artifact
7. inspect `.engram/artifacts/` to understand what happened across commands
8. maintain memories and project tools without tags/levels/superseding complexity
