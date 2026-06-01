# ADR 0001: CLI-First MVP Redesign

## Status

Accepted

## Context

Engram's current `main` branch is MCP-first. The CLI is currently a small companion interface, while most agent-facing behavior is exposed through MCP tools and resources.

This has made the product heavier than needed for the current target use case: a local-first project memory and workflow system used inside the same repository where the agent is working.

The current design also contains concepts that are too broad for the MVP:

- MCP server and MCP tools as the primary interface
- memory tags, types, scopes, levels, guardrails, and superseding
- workflow finish behavior that mixes verification, commit, push, and task completion
- terminal-only outputs that can be truncated or hard to audit

The MVP should prioritize local usability, auditability, and simple agent interaction.

## Decision

Engram MVP will be redesigned as a CLI-first local workflow system.

The stable core will be:

```text
CLI commands
  -> service layer
  -> models / local DB / Git helpers / artifact writer
```

MCP will be removed from the MVP surface. The service layer remains the application boundary so another adapter can be added later if needed.

## MVP Scope

The MVP includes these core concepts:

- project
- phase
- task
- memory
- project tool
- command artifact
- verification run

## Data and Runtime Storage

Engram will use a project-local ignored runtime directory:

```text
.engram/
  db/
  artifacts/
  inputs/
  templates/
```

The directory must be added to `.gitignore` by initialization unless already ignored.

Markdown artifact files are the readable source of truth for command output history.

The DB stores artifact metadata only, including:

- artifact ID
- project ID
- task ID, when relevant
- phase ID, when relevant
- command name
- status
- artifact path
- content hash
- short summary
- creation timestamp

The MVP will not duplicate full Markdown artifact bodies in the DB.

## Memory Model

The MVP memory model is intentionally simple.

Memories are plain project knowledge records retrieved by relevance. They do not have tags, levels, scopes, types, or superseding behavior.

Project tools are separate from memories. Project tools are always included in startup/task context and represent reusable project-specific instructions, commands, conventions, or tool notes.

Supported memory/project-tool maintenance operations for MVP:

- add
- list/read
- edit
- delete

No guardrail hierarchy is included in the MVP.

## Workflow Commands

The MVP workflow is centered on three user-facing workflow commands:

- `start`: select or resume the next task, prepare the working branch, retrieve relevant memory, include project tools, and write a startup artifact
- `verify`: run configured local verification checks and write a verification artifact
- `commit`: commit and push verified task work, then mark task state complete

Verification belongs in `verify`, not Git hooks. GitHub CI can be used as the remote enforcement layer.

`commit` should check whether the current task has a successful recent verification record before completing the task. It should not rerun all verification by default.

## Command Artifacts

Every Engram command writes a Markdown artifact, including small commands.

Terminal output should stay concise and point to the artifact path. The artifact contains the full command result, details, and next relevant context.

This gives:

- audit history
- debugging visibility
- agent-readable backlogs
- output-quality review
- protection against terminal truncation

## Structured Inputs

Commands with many fields may accept structured input files.

Use simple CLI arguments for small commands. Use YAML input files for multi-field or bulk operations, especially task planning and updates.

Templates should be provided so agents do not guess input structure.

## Consequences

### Positive

- simpler product surface
- easier Codex/agent usage
- better debugging and auditability
- less context noise than MCP output wrapping
- service layer remains reusable
- artifact history improves workflow continuity

### Negative

- removes MCP interoperability from the MVP
- local `.engram/` runtime directory must be maintained
- artifact output quality becomes part of product quality
- DB path behavior changes from global-first to project-local runtime storage

## Out of Scope

The MVP will not include:

- MCP server or tools
- web UI
- artifact search
- artifact pruning policies
- artifact compression
- full artifact body storage in DB
- memory tags, levels, types, scopes, or superseding
- complex audit event taxonomy
- multiple output formats
- automatic Git hooks
