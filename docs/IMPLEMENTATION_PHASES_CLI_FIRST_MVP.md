# Implementation Phases: CLI-First Engram MVP

## Phase 1: Remove MCP from the MVP Surface

### Description

Move the product direction from MCP-first to CLI-first. MCP code can be deleted or isolated depending on implementation risk, but it must not remain the primary MVP interface.

### Output

- MCP-first docs removed or rewritten
- MCP script/dependency removed from active MVP path
- MCP-specific tests removed, skipped, or replaced
- README describes Engram as CLI-first

### Acceptance

- Installing and using MVP Engram does not require MCP
- Active documentation no longer instructs users to configure an MCP client
- Core behavior is accessible through CLI and services

### Out of Scope

- MCP compatibility layer
- alternate agent protocol adapters

---

## Phase 2: Establish Project-Local Runtime Storage

### Description

Create the project-local `.engram/` runtime directory structure and ensure it is ignored by Git.

### Output

- `.engram/` initialization behavior
- runtime subdirectories for DB, artifacts, inputs, and templates
- Git ignore handling
- migration path from current global DB behavior, if needed for existing tests/users

### Acceptance

- New projects initialize `.engram/` locally
- `.engram/` is not committed by default
- Engram commands can resolve the active project runtime directory

### Out of Scope

- cloud sync
- artifact pruning
- multi-repo shared runtime DB

---

## Phase 3: Add Command Artifact Infrastructure

### Description

Implement shared infrastructure so every Engram command writes a Markdown artifact and DB metadata record.

### Output

- command artifact service
- command artifact DB table
- artifact path generation
- content hashing
- common command result/status handling

### Acceptance

- every CLI command creates an artifact file
- every artifact has a DB metadata row
- terminal output can stay concise while full details are saved
- artifact bodies are not duplicated in the DB

### Out of Scope

- artifact search
- artifact compression
- artifact retention policies
- artifact UI

---

## Phase 4: Simplify Memory and Add Project Tools

### Description

Replace the over-designed memory model with plain memories and separate always-included project tools.

### Output

- simplified memory schema/service behavior
- project tools schema/service behavior
- startup context uses relevant memories plus all project tools
- removed guardrail/superseding/type/tag/level behavior from MVP path

### Acceptance

- memories can be added, listed, read, edited, deleted, and retrieved by relevance
- project tools can be added, listed, edited, deleted, and always included in startup context
- MVP behavior does not require memory tags, types, levels, scopes, or superseding

### Out of Scope

- memory audit automation beyond basic add/edit/delete
- memory quality scoring
- guardrail hierarchy

---

## Phase 5: Build CLI Wrappers Over Services

### Description

Expand the CLI so it becomes the primary interface while keeping business behavior inside services.

### Output

- CLI wrappers for project, phase, task, memory, project tool, and artifact-aware commands
- consistent error handling
- concise terminal rendering
- artifact creation for all command paths

### Acceptance

- CLI commands call service functions rather than duplicating business logic
- command failures still write useful failed artifacts where practical
- service layer remains testable without CLI execution

### Out of Scope

- exact final terminal copy/layout polish
- non-Markdown output formats

---

## Phase 6: Implement Core Workflow Commands

### Description

Implement the required task workflow: `start`, `verify`, and `commit`.

### Output

- `start` workflow using task selection, branch preparation, memory retrieval, project tools, and startup artifact
- `verify` workflow using local configured checks and verification artifact
- `commit` workflow using verification record, Git commit/push, task completion, and commit artifact

### Acceptance

- a user can start or resume a task from CLI
- verification runs are recorded and linked to the active task when relevant
- commit refuses unverified task completion by default
- successful commit marks the task done only after commit/push succeeds

### Out of Scope

- Git hooks
- automatic remote PR creation
- background verification
- CI orchestration beyond documenting GitHub CI as external guardrail

---

## Phase 7: Add Structured Input Templates

### Description

Support YAML input files for commands with many fields or bulk operations, while keeping simple commands argument-based.

### Output

- YAML input parsing for selected complex commands
- templates for task/phase/memory/project-tool creation or updates
- validation errors that point to invalid fields clearly

### Acceptance

- agents do not need to pass large multi-field payloads through long command arguments
- simple commands remain simple
- templates are available after initialization or through a documented command

### Out of Scope

- full schema language
- JSON/YAML dual-format support unless trivial
- interactive form generation

---

## Phase 8: Update Tests and Documentation

### Description

Align tests and docs with the CLI-first MVP.

### Output

- updated README
- updated user manual or removed stale MCP-specific manual content
- service tests updated for simplified memory/project-tool behavior
- CLI tests for artifact-producing commands
- workflow tests for start/verify/commit

### Acceptance

- test suite passes without MCP as a required dependency
- docs describe the implemented MVP accurately
- old MCP-first behavior is not presented as the default product path

### Out of Scope

- exhaustive docs polish
- tutorial site
- external package publishing

---

## MVP Completion Criteria

The MVP is complete when:

- Engram can initialize a local repo runtime
- core data lives in local project storage
- every command writes a Markdown artifact and DB metadata row
- memories are simple relevance-retrieved records
- project tools are separate and always included in startup context
- `start`, `verify`, and `commit` support the main agent workflow
- CLI is the primary interface
- MCP is no longer required or documented as the MVP path
