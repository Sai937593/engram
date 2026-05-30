# Codex Implementation Phases: Engram Workflow Redesign

## Purpose

This document breaks the workflow redesign into implementation phases for Codex.

Use this with:

- `docs/CODEX_HANDOFF_WORKFLOW_REDESIGN.md`

The handoff doc defines the product decisions. This document defines a safe build sequence.

---

## Build Principles

- Preserve the decision locks from the handoff doc.
- Prefer small, testable phases over one large rewrite.
- Use repo-local `.engram/memory.db` as the only normal project state store.
- Make Engram MCP-first; normal Codex workflows must not depend on CLI commands.
- Keep Python + uv packaging/runtime.
- Skills and workflow guidance must respect the current/base branch instead of assuming `main`.
- Keep primary workflow tools compact and Markdown-first.
- Do not add Project Card as a new abstraction.
- Do not force memory creation for every task; force memory review only.
- Keep CRUD/lifecycle tools as support/admin tools, not the main workflow path.
- Avoid raw database write access from agents.

---

## Phase 0: Baseline Audit and External Skill Update

### Goal

Confirm the current MCP, storage, task, memory, phase, workflow, and skill-bank surfaces before making product changes, and update the external Engram transition skill so it does not accidentally target `main`.

### Work

- Inspect current DB path and project resolution behavior.
- Inspect CLI-only behavior that needs MCP/service parity.
- Inspect current MCP server startup and stdio entrypoint behavior.
- Inspect current workflow tools.
- Inspect current branch creation / merge / phase-transition assumptions.
- Inspect the external Codex/Engram transition skill instructions for hardcoded `main` assumptions.
- Before product-code changes, update the external Engram transition skill so it:
  - detects or respects the current active redesign/base branch
  - creates phase/task branches from that branch
  - targets merges/PRs back to that branch
  - does not merge, rebase, or open PRs into `main` unless the user explicitly asks
- Inspect task lifecycle and task schema.
- Inspect memory lifecycle support.
- Inspect phase lifecycle support.
- Inspect startup context / guardrail rendering.
- Inspect existing tests around MCP tools, context, tasks, memory, storage, branch behavior, and workflow.

### Output

- Short implementation note identifying current gaps and files to modify.
- Confirmation that the external Engram transition skill was updated before product implementation.
- Branch policy note stating the active redesign/base branch and how phase/task branches should target it.
- No product behavior changes unless needed to unblock later phases.

### Acceptance

- Current behavior is understood.
- Existing tests still pass.
- Later phases have clear file targets.
- Codex has explicit branch guidance before any workflow/phase-transition changes.
- The external Engram transition skill no longer instructs agents to merge/target `main` by default.

---

## Phase 1: Repo-Local DB Foundation

### Goal

Move normal project state from global DB/project binding to repo-local `.engram/memory.db`.

### Work

- Add repo/workspace root discovery for MCP/service usage.
- Store project state in `project-root/.engram/memory.db`.
- Initialize repo-local DB schema and project metadata.
- Add `.engram/` to `.gitignore` during project initialization.
- Replace global repo-path binding with repo-local project resolution.
- Keep any global storage only as temporary migration/legacy support if needed.

### Acceptance

- New projects use `.engram/memory.db` by default.
- Project resolution no longer depends on scanning a global DB for `repo_paths`.
- Missing repo-local DB returns a clear not-initialized state.
- Existing tests are updated to use repo-local DB assumptions.

---

## Phase 2: MCP-First Project Init and Diagnostics

### Goal

Ensure Codex can initialize and inspect Engram state through MCP without CLI dependency.

### Work

- Add/refine MCP tool for project initialization.
- Add/refine MCP tool/resource for current project status.
- Add/refine MCP diagnostics for DB existence, schema health, repo root detection, and `.gitignore` status.
- Ensure the same MCP command can work across projects when launched from the project workspace.
- Avoid requiring per-project MCP command changes.

### Acceptance

- Codex can initialize a new repo through MCP.
- Codex can inspect project status through MCP.
- Uninitialized repos produce actionable MCP output.
- Normal workflows do not require CLI commands.

---

## Phase 3: Remove CLI as Workflow Dependency

### Goal

Migrate CLI-owned behavior into services and MCP tools/resources.

### Work

- Identify CLI-only functionality still needed by agents.
- Move required behavior into service-layer functions.
- Expose required behavior through MCP tools/resources.
- Update docs so normal workflow is MCP-first.
- Keep, reduce, or remove CLI only after MCP/service parity exists.

### Acceptance

- No normal Codex workflow depends on CLI.
- No new workflow functionality exists only in CLI.
- CLI, if retained, is limited to optional human diagnostics/migration.

---

## Phase 4: Packaging and MCP Startup Reliability

### Goal

Keep Python + uv while making MCP startup deterministic and reliable.

### Work

- Preserve `engram-mcp` stdio entrypoint behavior.
- Ensure startup does not initialize or depend on a global project DB.
- Ensure startup can discover the current repo/workspace and report uninitialized state cleanly.
- Keep tool schemas stable and errors actionable.
- Do not rewrite in Node/npm.

### Acceptance

- MCP server starts reliably through the existing Python/uv path.
- Startup behavior is deterministic across repos.
- Packaging remains Python + uv.
- No Node/npm migration is introduced.

---

## Phase 5: Markdown-First Workflow Output Contract

### Goal

Define and apply compact Markdown output contracts for primary workflow tools.

### Work

- Replace YAML-style workflow output with Markdown-first output for primary workflow responses.
- Ensure workflow outputs avoid duplicated task/phase/status metadata.
- Ensure each workflow output has exactly one `Next action` section.
- Add stable output shapes for:
  - successful start
  - blocked start
  - verification passed
  - verification failed
  - finish blocked
  - finish succeeded

### Acceptance

- `workflow_start` returns a compact Work Order.
- `workflow_finish` no longer tells the agent to start the next task.
- Primary workflow outputs are readable as Markdown.
- Tests assert no duplicated obvious metadata and no auto-start-next-task guidance.

---

## Phase 6: Work Order Refinement for `workflow_start`

### Goal

Make `engram_workflow_start` the main task-entry point for Codex.

### Work

- Return objective, acceptance, relevant files/search hints, guardrails, task memories, boundaries, required gates, and next action.
- Keep output concise and state-aware.
- Include guardrails using existing L0/L1 memory concepts.
- Include task-relevant memories without dumping excessive history.
- Provide useful guidance when no task memory is found.

### Acceptance

- `workflow_start` gives Codex enough starting context to avoid scanning the whole codebase.
- Guardrails and relevant task memories are present when available.
- Empty memory state provides useful search guidance.
- Output remains compact.

---

## Phase 7: Add `engram_workflow_verify`

### Goal

Add the required verification gate before finish.

### Work

- Add a workflow verification command/tool.
- Run the project’s local quality checks.
- Return concise pass/fail Markdown.
- Summarize the first actionable failure instead of dumping long logs.
- Store enough verification state to determine whether finish is allowed.

### Acceptance

- `engram_workflow_verify` exists as a primary workflow tool.
- Verification pass/fail is visible and concise.
- Failure output identifies the first fix target when possible.
- Verification state can be checked by `workflow_finish`.

---

## Phase 8: Verification Gate in `workflow_finish`

### Goal

Prevent finishing tasks without a valid verification pass.

### Work

- Make `workflow_finish` check verification status before commit/finish.
- Block finish if verification never ran.
- Block finish if verification failed.
- Block finish if verification is stale after relevant changes.
- Return a compact blocked response with one next action.

### Acceptance

- `workflow_finish` cannot complete an unverified task.
- Blocked output clearly tells Codex to run or rerun `workflow_verify`.
- Successful finish remains concise.

---

## Phase 9: Memory Review Skill + Gate

### Goal

Force memory hygiene without forcing memory creation.

### Work

- Add a Memory Review Skill.
- Add a way to record memory review outcome for the active task.
- Support outcomes:
  - memory created
  - memory superseded
  - memory demoted
  - memory archived
  - memory deleted
  - no memory change needed
- Make `workflow_finish` block if memory review outcome is missing.
- Keep detailed review instructions in the skill, not in tool output.

### Acceptance

- Codex is directed to run the Memory Review Skill after verification passes.
- `workflow_finish` blocks until memory review is recorded.
- No task is forced to create memory when no durable knowledge changed.
- Memory review outcome is visible in finish output.

---

## Phase 10: Task Decomposition Skill

### Goal

Prevent weak task creation when Codex converts phase docs into Engram tasks.

### Work

- Add a Task Decomposition Skill for converting implementation phase docs into executable tasks.
- Specify expected task fields:
  - title
  - objective / description
  - acceptance criteria
  - relevant files
  - search hints
  - dependencies
  - verification guidance
  - out-of-scope boundaries
  - risk notes when needed
- Make the skill explicit about which `engram_task_create` fields to populate.

### Acceptance

- The skill gives Codex clear guidance for creating complete tasks.
- The skill discourages tasks with only title/description/dependency.
- The skill is reusable for future phase intake sessions.

---

## Phase 11: Draft → Ready Task Lifecycle

### Goal

Ensure incomplete tasks cannot be selected by `workflow_start`.

### Work

- Add or refine task states to distinguish incomplete tasks from executable tasks.
- Introduce task validation before a task can become ready.
- Ensure `workflow_start` selects only ready tasks.
- Provide blocked output when no ready tasks exist but draft tasks need validation/fixes.

### Acceptance

- Draft/incomplete tasks cannot start.
- Ready tasks satisfy minimum quality metadata.
- Codex gets clear feedback when task metadata is missing.

---

## Phase 12: Task Quality Validation

### Goal

Create a quality gate for task metadata.

### Work

- Validate presence and quality of:
  - objective / description
  - acceptance criteria
  - relevant files or search hints
  - verification guidance
  - dependencies if applicable
  - out-of-scope boundaries when useful
- Return actionable validation failures.
- Allow Codex to fix task metadata and rerun validation.

### Acceptance

- Invalid tasks are rejected from ready state.
- Validation output points to missing or weak fields.
- Codex can iterate from draft to ready without guessing.

---

## Phase 13: Memory Lifecycle Tool Refinement

### Goal

Give Codex safe domain-level write access for memory hygiene.

### Work

- Add/refine memory tools for:
  - get
  - update
  - supersede
  - demote
  - archive
  - delete
- Prefer supersede/archive/demote over delete.
- Keep normal search/list behavior excluding superseded/archived memories unless explicitly requested.
- Refine `engram_memory_search` output to compact Markdown.

### Acceptance

- Codex can maintain memory freshness without raw DB access.
- Memory search output is useful and compact.
- Stale memories can be safely superseded, demoted, or archived.

---

## Phase 14: Phase and Task Lifecycle Tool Refinement

### Goal

Complete domain-level lifecycle support around the primary workflow.

### Work

- Add/refine task tools for:
  - update
  - block
  - unblock
  - cancel
  - archive/delete
- Add/refine phase tools for:
  - update
  - cancel
  - archive
- Keep lifecycle tools separate from the primary execution path.

### Acceptance

- Codex can maintain phase/task state safely.
- Lifecycle tools do not replace the main execution loop.
- Invalid lifecycle transitions are blocked or clearly explained.

---

## Phase 15: End-to-End Workflow Tests

### Goal

Prove the redesigned workflow works as intended.

### Work

Add tests for:

- new repo -> MCP project init -> repo-local DB available
- MCP startup reports uninitialized repo clearly
- normal workflow does not require CLI
- external Engram transition skill does not hardcode `main` as the integration target
- phase doc -> draft tasks -> validation -> ready tasks
- `workflow_start` selects only ready tasks
- `workflow_verify` records pass/fail state
- `workflow_finish` blocks without verification
- `workflow_finish` blocks without memory review
- memory review no-change path
- memory review with create/supersede path
- finish output does not auto-start next task
- Markdown output contracts remain stable

### Acceptance

- End-to-end new-project session is covered.
- End-to-end task session is covered.
- End-to-end phase-splitting session is covered.
- Branch-aware external transition skill guidance is covered.
- Regression tests protect the major decision locks.

---

## Suggested Build Order

```text
0. Baseline audit and external skill update
1. Repo-local DB foundation
2. MCP-first project init and diagnostics
3. Remove CLI as workflow dependency
4. Packaging and MCP startup reliability
5. Markdown workflow output contract
6. Work Order refinement
7. workflow_verify
8. verification gate in workflow_finish
9. memory review skill + gate
10. task decomposition skill
11. draft -> ready lifecycle
12. task quality validation
13. memory lifecycle refinement
14. phase/task lifecycle refinement
15. end-to-end tests
```

---

## Stop Conditions

Pause and ask for user review if a phase requires changing any decision lock from the handoff doc, especially:

- assuming `main` is always the integration branch
- using global DB as normal project storage
- relying on repo-path binding for project resolution
- requiring CLI for normal Codex workflows
- adding workflow functionality only in CLI
- rewriting Engram in Node/npm
- adding Project Card as a new abstraction
- forcing memory creation for every task
- making CRUD tools the main workflow path
- auto-starting the next task after finish
- exposing raw database writes
- moving detailed skill reasoning into large tool outputs
