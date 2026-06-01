# ADR 0002: Workflow MVP Simplification

## Status

Accepted.

## Context

The workflow redesign branch introduced useful foundations for Engram:

- repo-local project state under `.engram/`
- MCP-first workflow tools
- task/phase/memory services
- workflow start, verify, and finish gates
- memory lifecycle tooling
- Markdown-oriented agent outputs

The design became heavier than needed for the current MVP. The MVP is intended for personal use and portfolio-quality implementation, not multi-user enterprise workflow management. The main risk is not missing enterprise features; the main risk is agent confusion caused by too many states, gates, and tools.

This ADR narrows the product to the smallest useful workflow:

```text
start task -> implement -> verify -> finish and commit
```

Memory review moves out of every task and into phase completion. Root `AGENTS.md` stores only stable project rules. Engram stores tasks, phases, and simple searchable memories.

## Decision

Engram will simplify the workflow redesign into an MCP-first MVP with the following decisions.

### 1. Keep MCP as the primary agent interface

MCP remains the normal interface for agents. The CLI may remain for human diagnostics, migration, or fallback use, but normal agent workflows should not depend on CLI output parsing.

### 2. Keep repo-local project state

Engram state remains repo-local by default:

```text
.engram/memory.db
```

This keeps project state portable with the repository while still allowing `.engram/` to stay ignored by Git unless explicitly needed.

### 3. Use a lean root `AGENTS.md`

Root `AGENTS.md` should contain stable project rules only:

- project guardrails
- architecture rules
- coding conventions
- behavioral expectations
- branch policy
- testing expectations

It should not contain large workflow instructions, detailed task history, or noisy memories.

Detailed Engram task workflow instructions belong in the start-task skill, not in root `AGENTS.md`.

### 4. Add inactive agent-file templates

The repository will include inactive source templates under `agent-files/`. Template files must not be named `AGENTS.md` or `SKILL.md`, because those names may be auto-loaded by agent environments.

Target structure:

```text
agent-files/
  root-agents-template.md
  skills/
    engram-start-task-template.md
    engram-task-decomposition-template.md
    engram-phase-review-template.md
```

Active skill files may be copied into the actual agent skill location, for example:

```text
.codex/skills/<skill-name>/SKILL.md
```

### 5. Simplify task lifecycle

Tasks should be executable when created. Engram should not create incomplete planning drafts as tasks.

Remove the user-facing draft/ready/todo lifecycle. Use a minimal lifecycle:

```text
open
in_progress
blocked
done
cancelled
```

A task has `is_verified`, initialized to `false`.

Task creation must validate required fields before writing to the database. If validation fails, no task is created.

Required fields:

- title
- objective
- acceptance
- phase_id
- verification
- relevant_files or search_hints

Validation errors must be detailed and actionable.

### 6. Rename finish to `finish_and_commit`

The current finish tool commits and pushes work, so its name should make that side effect explicit.

Target primary tool:

```text
engram_workflow_finish_and_commit
```

The old tool name may remain temporarily as a deprecated alias:

```text
engram_workflow_finish
```

The alias should clearly tell the agent to use `engram_workflow_finish_and_commit`.

### 7. Verification owns staging

Engram will use Git's index as the verification boundary.

`engram_workflow_verify`:

1. Runs configured local checks.
2. If any check fails, sets or leaves `task.is_verified = false`.
3. If all checks pass, runs `git add -A`.
4. Sets `task.is_verified = true`.

`engram_workflow_finish_and_commit`:

1. Requires an active task.
2. Requires `task.is_verified == true`.
3. Requires no unstaged changes.
4. Requires no untracked files.
5. Commits the already-staged verified changes.
6. Pushes.
7. Marks the task done.

`finish_and_commit` must not run `git add -A`. Only verify stages work.

This avoids diff hashes and timestamp tracking while still catching normal edits made after verification.

### 8. Move local hook checks into verify

The workflow should not depend on Git hooks.

The local verification tool should run the checks needed before commit. The initial target command set is:

```bash
uv run ruff format .
uv run ruff check . --fix
uv run python -m engram.hooks.py_structure
uv run pytest tests/ -m "not slow" -x --tb=short -q
```

CI remains the final external guardrail and may run stricter or broader checks.

### 9. Move memory review to phase completion

Per-task memory review is removed from the finish gate.

Task workflow:

```text
engram_workflow_start
implement
engram_workflow_verify
engram_workflow_finish_and_commit
```

Phase completion workflow:

```text
phase verification
memory review using memory CRUD tools
update root AGENTS.md only for stable project rules
complete phase
```

### 10. Simplify memory interface

The user-facing memory model becomes simple CRUD.

Expose these tools:

```text
engram_memory_list
engram_memory_get
engram_memory_create
engram_memory_update
engram_memory_update_many
engram_memory_delete
engram_memory_delete_many
```

Remove or hide from the normal agent-facing interface:

- tags
- levels
- demote
- supersede
- always_include
- scope
- memory types

The existing database schema may keep extra columns internally during migration, but the agent-facing model should be simple.

### 11. Add targeted batch tools

Batch tools are useful for phase-level memory review and task decomposition.

Add:

```text
engram_memory_update_many
engram_memory_delete_many
engram_task_create_many
```

`engram_task_create_many` must be transactional. If any task is invalid, create no tasks and return detailed per-task validation errors.

Do not add a generic arbitrary batch mutation tool in the MVP.

### 12. Do not add Markdown report artifacts yet

MCP output is enough for now. Do not add `.engram/reports/*.md` until output size becomes a real problem.

## Consequences

### Positive

- Simpler agent workflow.
- Fewer states and gates.
- Less context noise in root `AGENTS.md`.
- Clear distinction between stable project rules and searchable memories.
- Verification has one practical boundary: staged verified changes.
- Memory review happens where it is useful: phase completion.

### Negative / accepted tradeoffs

- `is_verified` plus staged-change checking is not a malicious-agent security boundary.
- Removing per-task memory review may miss some task-level lessons unless phase review is done consistently.
- Simplifying memory CRUD loses explicit supersession/demotion semantics in the user-facing interface.
- Keeping old DB columns internally may create temporary mismatch between schema and public tools.

These tradeoffs are acceptable for the MVP.

## Non-goals

- No enterprise task workflow.
- No multi-project dashboard.
- No global memory database as the primary store.
- No complex memory taxonomy.
- No mandatory Git hooks.
- No generic mutation batch tool.
- No report artifact system yet.
- No automatic phase memory-review tool; the phase-review skill will use normal memory tools.

## Implementation note

This ADR supersedes the parts of ADR 0001 that require per-task memory review, draft/ready task gates, and a more complex memory lifecycle as the normal agent-facing interface. It does not supersede the repo-local storage or MCP-first decisions from ADR 0001.
