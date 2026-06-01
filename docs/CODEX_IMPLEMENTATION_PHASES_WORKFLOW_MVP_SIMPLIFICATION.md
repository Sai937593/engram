# Codex Implementation Phases: Workflow MVP Simplification

> Historical implementation planning document. Active agent-facing workflow guidance should be taken from `docs/USER_MANUAL.md` and skill instructions.

## Branch

```text
feat/workflow-mvp-simplification
```

## Primary docs

Read in this order:

1. `docs/adr/0002-workflow-mvp-simplification.md`
2. `docs/CODEX_HANDOFF_WORKFLOW_MVP_SIMPLIFICATION.md`
3. this implementation plan

## Build principle

Keep the implementation small. Prefer removing states, gates, and tool concepts over adapting the old complex workflow.

The target task loop is:

```text
start -> implement -> verify -> finish_and_commit
```

## Phase 0: Baseline audit

### Goal

Understand the existing workflow redesign implementation before changing it.

### Tasks

- Inspect current task status validation.
- Inspect task creation/update services.
- Inspect current workflow start/verify/finish services.
- Inspect MCP tool registration.
- Inspect memory tool and lifecycle tool registration.
- Inspect tests covering workflow, task validation, and memory tools.

### Deliverable

Short implementation note in the PR or commit summary explaining which files will be changed.

### Acceptance

- No behavior change yet.
- Codex knows where task statuses, verification, finish gating, and memory tools are implemented.

## Phase 1: Agent file bootstrap

### Goal

Ensure the repository has lean project instructions and inactive reusable templates.

### Tasks

- Add or update root `AGENTS.md` with stable project rules only.
- Add `agent-files/root-agents-template.md`.
- Add `agent-files/skills/engram-start-task-template.md`.
- Add `agent-files/skills/engram-task-decomposition-template.md`.
- Add `agent-files/skills/engram-phase-review-template.md`.
- Ensure inactive templates are not named `AGENTS.md` or `SKILL.md`.

### Acceptance

- Root `AGENTS.md` is lean.
- Detailed task workflow instructions live in the start-task template.
- Templates can be copied into active agent locations without rewriting.

## Phase 2: Task model simplification

### Goal

Make tasks executable at creation time and remove draft/ready/todo complexity from the normal workflow.

### Tasks

- Replace normal statuses with:

```text
open
in_progress
blocked
done
cancelled
```

- Add or expose `is_verified` on tasks, initialized to `false`.
- Update task creation validation to require:
  - title
  - objective
  - acceptance
  - phase_id
  - verification
  - relevant_files or search_hints
- Ensure invalid task creation writes nothing.
- Ensure validation errors are detailed and actionable.
- Update task listing/selection logic to use `open` as the executable queue status.
- Update status migration or compatibility handling as needed for existing databases.

### Acceptance

- Creating a task with missing required fields fails with no DB write.
- Error response lists missing fields and retry guidance.
- New task starts as `open` and `is_verified = false`.
- Workflow start selects `open` tasks.
- Old draft/ready/todo concepts are not part of the documented MVP workflow.

## Phase 3: Batch task creation

### Goal

Support task decomposition without creating partial task sets.

### Tasks

- Add service function for create-many.
- Add MCP tool:

```text
engram_task_create_many
```

- Validate all tasks before writing.
- Use all-or-nothing behavior.
- Return detailed per-task validation errors.

### Acceptance

- If all tasks are valid, all are created.
- If any task is invalid, zero tasks are created.
- Response identifies exactly which task entries failed and why.

## Phase 4: Verification owns checks and staging

### Goal

Make `engram_workflow_verify` the single local verification gate.

### Target commands

```bash
uv run ruff format .
uv run ruff check . --fix
uv run python -m engram.hooks.py_structure
uv run pytest tests/ -m "not slow" -x --tb=short -q
```

### Tasks

- Update verification service to run the target commands.
- If a command fails:
  - set or leave `is_verified = false`
  - return command, exit code, and useful output tail
  - do not stage as verified
- If all commands pass:
  - run `git add -A`
  - set `is_verified = true`
  - return verified-and-staged message
- Ensure verification requires an active task.

### Acceptance

- Passing verify stages all current changes.
- Passing verify sets `is_verified = true`.
- Failing verify sets/leaves `is_verified = false`.
- Verify output is concise but actionable.

## Phase 5: Finish-and-commit tool

### Goal

Make the commit side effect explicit and protect the verification boundary.

### Tasks

- Add primary MCP tool:

```text
engram_workflow_finish_and_commit
```

- Implement service behavior:
  1. require active in-progress task
  2. require `is_verified == true`
  3. require no unstaged changes
  4. require no untracked files
  5. commit already-staged changes
  6. push
  7. mark task done
- Ensure this function does not run `git add -A`.
- Keep `engram_workflow_finish` temporarily as a deprecated alias or wrapper.
- Update formatter output and docs to prefer `finish_and_commit`.

### Acceptance

- Finish blocks when task is not verified.
- Finish blocks when unstaged changes exist after verify.
- Finish blocks when untracked files exist after verify.
- Finish commits only already-staged changes.
- Finish marks task done only after commit/push succeeds.
- Old finish name is no longer the primary documented flow.

## Phase 6: Remove per-task memory-review gate

### Goal

Make finish independent of memory review.

### Tasks

- Remove finish blocking based on memory-review outcome.
- Remove task-flow instructions requiring per-task memory review.
- Keep any existing memory fields only if needed for backwards compatibility.
- Update tests expecting finish to block on missing memory review.

### Acceptance

- Task finish does not require memory review.
- Memory review is documented as phase-level work.
- Start/verify/finish task flow is clean.

## Phase 7: Simplify memory interface

### Goal

Expose simple memory CRUD to agents.

### Tasks

- Add/confirm MCP tools:

```text
engram_memory_list
engram_memory_get
engram_memory_create
engram_memory_update
engram_memory_delete
```

- Hide/remove normal agent-facing dependence on:
  - tags
  - levels
  - demote
  - supersede
  - always_include
  - scope
  - memory types
- Keep internal schema fields temporarily if easier.
- Update memory output to show only simple fields by default:
  - id
  - title
  - content preview or content
  - created_at
  - updated_at

Historical note: the removed lifecycle concepts above are implementation migration context, not active instructions for routine agent work.

### Acceptance

- Agent can list, read, create, update, and delete memories without raw DB access.
- Normal docs do not instruct agents to use demote/supersede/levels/tags.
- Memory output is compact and readable.

## Phase 8: Batch memory operations

### Goal

Make phase-level memory review efficient.

### Tasks

- Add:

```text
engram_memory_update_many
engram_memory_delete_many
```

- Validate IDs and payloads before mutation.
- Prefer all-or-nothing behavior.
- Return concise summary.

### Acceptance

- Multiple memories can be updated in one tool call.
- Multiple memories can be deleted in one tool call.
- Invalid IDs or payloads produce clear errors.
- No generic arbitrary batch mutation tool is added.

## Phase 9: Phase-review skill alignment

### Goal

Make phase review work with only normal phase/task/memory tools.

### Tasks

- Update phase-review skill/template to:
  - inspect completed phase tasks
  - inspect relevant memories using list/get
  - create/update/delete memories as needed
  - update root `AGENTS.md` only for stable project rules
  - complete the phase
- Do not add a special phase memory review start tool.

### Acceptance

- Phase review can be completed using existing/simple memory tools.
- No raw Python SQLite access is needed.
- Root `AGENTS.md` remains lean.

## Phase 10: Remove Git-hook dependency from docs and flow

### Goal

Ensure Engram workflow does not require Git hooks.

### Tasks

- Remove workflow documentation that says hooks are mandatory.
- Ensure verify runs local checks directly.
- Keep `.pre-commit-config.yaml` only if desired as optional developer convenience.
- Ensure CI remains separate from local verify.

### Acceptance

- Normal Engram workflow does not require pre-commit installation.
- Verify is the local quality gate.
- CI can still run full checks independently.

## Phase 11: Tests

### Goal

Cover the simplified MVP behavior.

### Required tests

Task creation:

- valid task creates successfully
- missing field creates nothing
- weak/invalid payload returns detailed error
- create-many all valid creates all
- create-many with one invalid creates none

Workflow verify:

- verify requires active task
- failed command leaves `is_verified = false`
- passing commands stage changes and set `is_verified = true`

Finish-and-commit:

- finish blocks when not verified
- finish blocks with unstaged changes
- finish blocks with untracked files
- finish does not run `git add -A`
- finish commits staged changes and marks task done

Memory:

- list/get/create/update/delete work through MCP/service layer
- update-many validates and applies changes
- delete-many validates and deletes

Phase review:

- no per-task memory review required
- phase review can use memory CRUD tools

### Acceptance

- All new tests pass.
- Existing tests are updated only where the old design has intentionally changed.

## Phase 12: Documentation cleanup

### Goal

Make the new MVP path obvious.

### Tasks

- Update README or docs index if present.
- Ensure Codex handoff points to ADR 0002.
- Mark older redesign docs as historical if they conflict.
- Update tool examples to use:

```text
engram_workflow_start
engram_workflow_verify
engram_workflow_finish_and_commit
```

### Acceptance

- A new agent can identify the simplified MVP docs quickly.
- Conflicting old guidance is explicitly historical or superseded.
- No docs tell agents to use per-task memory review as a finish gate.

## Final acceptance checklist

The simplification is complete when all are true:

- MCP remains primary.
- Repo-local `.engram/memory.db` remains primary state.
- Root `AGENTS.md` is lean.
- `agent-files/` contains inactive templates.
- Task creation is strict and non-partial.
- Task statuses are simple in normal workflow.
- `is_verified` starts false.
- Verify runs local checks and stages on pass.
- Finish-and-commit requires verified state and clean unstaged/untracked working tree.
- Finish-and-commit does not stage files.
- Per-task memory review is gone.
- Phase-level memory review uses normal memory tools.
- Memory interface is simple CRUD plus batch update/delete.
- No Git hooks are required for normal workflow.
- No Markdown report artifacts are added.
