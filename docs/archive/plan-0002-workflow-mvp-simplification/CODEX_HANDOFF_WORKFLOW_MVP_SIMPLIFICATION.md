# Codex Handoff: Workflow MVP Simplification

> Archived historical handoff document. Superseded by `docs/adr/0002-workflow-mvp-simplification.md`, `README.md`, and `docs/USER_MANUAL.md`. Do not treat this as active agent-facing workflow guidance.

## Purpose

Implement the simplified Engram workflow MVP on branch:

```text
feat/workflow-mvp-simplification
```

This branch is based on the prior workflow redesign branch. Keep useful foundations from that branch, but simplify the product surface.

The target MVP is:

```text
start task -> implement -> verify -> finish and commit
```

Phase-level planning and memory review remain, but per-task memory-review gating and complex memory lifecycle semantics are removed from the normal agent-facing workflow.

## Primary design source

Read first:

```text
docs/adr/0002-workflow-mvp-simplification.md
```

Then use this handoff as the implementation-oriented guide.

## Current branch assumptions

The current redesign branch already has many foundations that should be reused where practical:

- repo-local `.engram/memory.db`
- MCP server and tool registration
- workflow start/verify/finish tools
- task, phase, and memory services
- memory lifecycle tools
- workflow verification persistence
- Markdown-oriented output formatters

Do not restart from `main` unless required by a concrete conflict.

## High-level product target

### Main task workflow

```text
engram_workflow_start
agent implements scoped task
engram_workflow_verify
engram_workflow_finish_and_commit
```

### Phase completion workflow

```text
phase verification
memory review using normal memory CRUD tools
update root AGENTS.md only if stable project rules changed
engram_phase_complete
```

### Root agent file role

Root `AGENTS.md` should contain stable project rules only. Detailed Engram task workflow instructions belong in the start-task skill, not in root `AGENTS.md`.

### Agent templates

Inactive templates live under:

```text
agent-files/
```

Template files must not be named `AGENTS.md` or `SKILL.md`.

## Required changes

## 1. Agent file bootstrap

Ensure the repo has active and inactive agent guidance files.

Target inactive templates:

```text
agent-files/
  root-agents-template.md
  skills/
    engram-start-task-template.md
    engram-task-decomposition-template.md
    engram-phase-review-template.md
```

Active files may exist under the actual Codex skill path:

```text
.codex/skills/<skill-name>/SKILL.md
```

Do not rename inactive templates to `AGENTS.md` or `SKILL.md`.

## 2. Task model simplification

Replace the user-facing task lifecycle with:

```text
open
in_progress
blocked
done
cancelled
```

Remove normal agent dependence on:

```text
draft
ready
todo
```

Tasks should be executable when created. Do not write incomplete tasks to the database.

### Required task creation fields

Task creation must require:

- title
- objective
- acceptance
- phase_id
- verification
- relevant_files or search_hints

If validation fails:

- create no task
- return a detailed error
- include missing fields
- include weak fields when possible
- tell the agent exactly how to retry

### `is_verified`

Add or expose a task verification flag:

```text
is_verified: bool = false
```

Newly created tasks must start with `is_verified = false`.

When a task changes in ways that invalidate verification, set `is_verified = false`.

## 3. Batch task creation

Add:

```text
engram_task_create_many
```

This is mainly for task decomposition.

Rules:

- validate every task first
- if any task is invalid, create no tasks
- return detailed per-task errors
- if all are valid, create all tasks

Do not add broad batch task mutation tools for the MVP unless needed by existing code paths.

## 4. Workflow verify owns local checks and staging

Update `engram_workflow_verify` so it is the local verification authority.

Target checks:

```bash
uv run ruff format .
uv run ruff check . --fix
uv run python -m engram.hooks.py_structure
uv run pytest tests/ -m "not slow" -x --tb=short -q
```

Behavior:

1. Require an active in-progress task.
2. Run checks in order.
3. If any command fails:
   - set or leave `is_verified = false`
   - return command, exit code, and useful output tail
   - do not mark verified
4. If all commands pass:
   - run `git add -A`
   - set `is_verified = true`
   - return that the task is verified and staged

`workflow_verify` may run formatting/fixing commands. That is expected.

## 5. Rename finish tool

Primary target tool:

```text
engram_workflow_finish_and_commit
```

Behavior:

1. Require active in-progress task.
2. Require `task.is_verified == true`.
3. Require no unstaged changes.
4. Require no untracked files.
5. Commit already-staged verified changes.
6. Push.
7. Mark task done.

Important:

```text
engram_workflow_finish_and_commit must not run git add -A.
```

Only verify stages work.

Keep old tool temporarily:

```text
engram_workflow_finish
```

Old tool may call the new implementation or return a deprecation message, but Codex-facing guidance should use `engram_workflow_finish_and_commit`.

## 6. Remove per-task memory review gate

Remove finish blocking based on memory-review outcome.

Task finish should require:

- active task
- task verified
- no unstaged/untracked changes after verification
- commit/push succeeds

Memory review now happens at phase completion.

## 7. Simplify memory tools

Expose a simple memory CRUD interface:

```text
engram_memory_list
engram_memory_get
engram_memory_create
engram_memory_update
engram_memory_update_many
engram_memory_delete
engram_memory_delete_many
```

Hide or remove from normal agent-facing workflow:

- tags
- levels
- demote
- supersede
- always_include
- scope
- memory types

It is acceptable for the database schema to keep extra columns during migration. The key requirement is that normal agent tools and docs present a simple model.

Historical note: the lifecycle fields listed above are migration/background context and are not part of routine agent instructions.

### Batch memory operations

Add:

```text
engram_memory_update_many
engram_memory_delete_many
```

Rules:

- validate all requested memory IDs
- fail safely with clear errors
- prefer all-or-nothing behavior unless implementation complexity is high
- return a concise summary of changed/deleted memories

Do not add a generic arbitrary batch mutation tool.

## 8. Phase-level memory review

Do not add a special `phase_memory_review_start` tool for the MVP.

The phase-review skill should use normal tools:

```text
engram_memory_list
engram_memory_get
engram_memory_create
engram_memory_update
engram_memory_delete
engram_memory_update_many
engram_memory_delete_many
```

During phase review, the agent should:

1. Review completed phase tasks.
2. Search/list existing memories.
3. Create durable new memories if needed.
4. Update stale memories if needed.
5. Delete wrong or obsolete memories if needed.
6. Update root `AGENTS.md` only for stable project rules.

## 9. No Git hooks as workflow dependency

Do not require pre-commit or pre-push hooks for the Engram workflow.

The repo may keep hook configuration temporarily, but Engram's local quality gate is `engram_workflow_verify`.

CI remains the final independent check.

## 10. No Markdown report artifacts yet

Do not implement `.engram/reports/*.md` for this MVP.

MCP responses should be concise and useful.

## Suggested implementation approach

Work in small commits.

Recommended order:

1. Add/update agent files.
2. Add ADR and docs.
3. Simplify task validation/model.
4. Add task create-many.
5. Update verify staging behavior.
6. Add `finish_and_commit` and deprecate old finish name.
7. Remove per-task memory-review finish gate.
8. Simplify memory tools.
9. Add batch memory tools.
10. Update tests and docs.

## Acceptance criteria

The implementation is complete when:

- A valid task can be created only with all required fields.
- Invalid task creation returns detailed errors and writes nothing.
- Task lifecycle uses the simplified statuses in normal workflow.
- `is_verified` starts false.
- `engram_workflow_verify` runs local checks, stages changes on pass, and sets `is_verified = true`.
- `engram_workflow_finish_and_commit` blocks when not verified.
- `engram_workflow_finish_and_commit` blocks if there are unstaged or untracked changes after verify.
- `engram_workflow_finish_and_commit` commits and pushes staged verified work without running `git add -A`.
- `engram_workflow_finish` is no longer the primary documented tool.
- Per-task memory review no longer blocks finish.
- Memory agent interface is simple CRUD plus batch update/delete.
- No special phase memory review tool is required.
- Root `AGENTS.md` stays lean.
- Detailed workflow behavior lives in the start-task skill.
- Normal workflow does not depend on Git hooks.
- Tests cover the main verify/finish gate behavior.

## Things not to do

- Do not add complex memory taxonomy.
- Do not add demote/supersede as normal agent-facing tools.
- Do not add generic batch mutation tools.
- Do not create incomplete tasks as drafts.
- Do not make root `AGENTS.md` a full workflow manual.
- Do not make CLI the required workflow interface.
- Do not add Markdown report artifacts yet.
- Do not make `finish_and_commit` stage files.
