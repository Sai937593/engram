# Engram User Manual

Engram is a local-first, agent-agnostic persistent memory system for AI coding assistants and developers. It stores durable project context in a repo-local SQLite database (`.engram/memory.db`) and exposes it through a custom Model Context Protocol (MCP) server, alongside a trimmed companion CLI for optional human setup and diagnostics.

The current standardized workflow is described in [ADR 0003](adr/0003-workflow-standardization.md). Active implementation phases live in [docs/plans/plan-0003-workflow-standardization/implementation-phases.md](plans/plan-0003-workflow-standardization/implementation-phases.md). Historical workflow docs are archived under [docs/archive/plan-0002-workflow-mvp-simplification/](archive/plan-0002-workflow-mvp-simplification/) and are reference material only.

---

## 1. Core Concepts

### Projects
A project maps to repo-local Engram state rooted in the current repository. When the MCP server or CLI utility commands are invoked from that workspace, Engram resolves the active project using the current working directory. Project and task state are persisted in `.engram/memory.db` inside the repository.

### Phases
Phases are first-class project milestones that group related tasks.
- Planning structure: `Project -> Phase -> Task`
- Lifecycle: `planned -> active -> review_pending -> done | blocked | cancelled`
- Only one phase is active per project. Activating a phase automatically demotes all other phases in the same project back to `planned`.
- Phase branch names are derived from explicit plan and phase keys when available, using `feat/<plan_key>-<phase_key>`.

### Tasks
Tasks are specific actionable units of work.
- Lifecycle: `open -> in_progress -> blocked -> done | cancelled`
- Priority levels: `low | medium | high | critical`
- Metadata: `title`, `description`, `acceptance`, `evidence`, `phase_id`, `tags`, `depends_on`, `relevant_files`, `verification`, and `key`.
- Verification: tasks carry `is_verified` to track whether the current workflow verification gate has passed.
- Planning path: non-trivial work should keep a task plan at `.engram/task-plans/<plan_key>/<phase_key>/<task_key>/task-plan.md`.
- Agents resolve task context and associated dependencies programmatically.

### Memories
Memories are persistent facts designed to survive across coding sessions.
- Normal interface: use memory CRUD (`list`, `get`, `create`, `update`, `delete`) for routine work.
- Retrieval: memories are indexed via SQLite FTS5 lexical search combined with local semantic search.
- Historical/internal detail: legacy lifecycle fields, supersession controls, and debug-only metadata may exist in the stored schema, but are not part of normal agent workflow guidance.

---

## 2. Command Reference

### Companion CLI Reference
The Engram command-line interface is trimmed to three optional human-facing workspace setup and utility commands:

#### `engram init`
```bash
engram init [--name NAME] [--id ID] [--summary SUMMARY]
```
Registers the current directory as an Engram project. If the repository is already registered, safely binds the current path to the existing project metadata.

#### `engram guide`
```bash
engram guide [concepts | commands | workflow | troubleshooting]
```
Opens this interactive user manual directly in the terminal, rendered as Markdown.

#### `engram db`
```bash
engram db
```
Utility command to print the absolute path, disk size, and SQLite integrity connection status of the repo-local database for the current workspace.

### Deprecated & Removed CLI Commands
To preserve clean separation of concerns and maintain a single source of truth, all programmatic memory, task, phase, and workflow management commands have been removed from the CLI. All agent interactions must go through the MCP server.

Refer to the table below to transition from the old CLI commands to their MCP server equivalents:

| Deprecated CLI Command | Status | MCP Server Equivalent |
| :--- | :--- | :--- |
| `engram context startup` | REMOVED | Read resource `engram://startup` |
| `engram context task <id>` | REMOVED | Read resource `engram://task/{task_id}/context` |
| `engram start` | REMOVED | Call tool `engram_workflow_start` |
| `engram finish` | REMOVED | Call tool `engram_workflow_finish_and_commit` (preferred) or transitional alias `engram_workflow_finish` |
| `engram task list` | REMOVED | Call tool `engram_task_list` |
| `engram task get` | REMOVED | Call tool `engram_task_get` |
| `engram task next` | REMOVED | Call tool `engram_task_next` |
| `engram task add` | REMOVED | Call tool `engram_task_create` |
| `engram task update` | REMOVED | Call tool `engram_task_update` |
| `engram task note` | REMOVED | Call tool `engram_task_note_append` |
| `engram task done` | REMOVED | Call tool `engram_task_done` |
| `engram memory add` / `decision add` | REMOVED | Call tool `engram_memory_create` |
| `engram memory search` | REMOVED | Call tool `engram_memory_search` |
| `engram phase list` / `get` / `start` | REMOVED | Call tools `engram_phase_*` |
| `engram export snapshot` | REMOVED | Read resource `engram://snapshot` |
| `engram export handoff` | REMOVED | Read resource `engram://handoff` |

Historical workflow docs are archived under `docs/archive/plan-0002-workflow-mvp-simplification/` and are not the active source of truth.

### MCP Interface Reference
Connected AI agents communicate with Engram using the standard STDIO-based Model Context Protocol.

#### Local Resources
Agents can read the following read-only Markdown resources:

* `engram://startup`: retrieves the startup context including active project details, active tasks, guardrails, and memory candidates.
* `engram://task/{task_id}/context`: retrieves a detailed requirement context for a single task including acceptance criteria, dependencies, and relevant lessons or decisions.
* `engram://snapshot`: returns a comprehensive project summary report compiling all phases, tasks, and memories.
* `engram://handoff`: returns a focused summary of recent phase completions, active tasks, and blockers.

#### Programmatic Tools
The MCP server exposes workflow, project, task, memory, and phase tools for full interactive capabilities.

List-style tools use a shared compact envelope with `ok`, `filters`, `count`, `items`, and `next_action`.

* Workflow control:
  * `engram_workflow_start`: starts the session workflow, claims the next actionable task, resolves the branch, and returns startup context.
  * `engram_workflow_verify`: runs local verification checks and stages changes on success.
  * `engram_workflow_finish_and_commit`: commits and pushes already-staged verified changes, then marks the task done.
  * `engram_workflow_finish`: deprecated transitional alias for `engram_workflow_finish_and_commit`.
* Project tools:
  * `engram_project_current`: returns the active project metadata resolved from the working directory.
  * `engram_project_init`: initializes a project in the current workspace.
  * `engram_project_diagnostics`: inspects repo root, DB health/schema, and `.gitignore` state.
* Task tools:
  * `engram_task_list`: filters and lists project tasks by status or phase.
  * `engram_task_get`: retrieves full details of a specific task.
  * `engram_task_next`: returns the highest-priority actionable open task.
  * `engram_task_create`: creates a new project task with explicit keys and execution metadata when needed.
  * `engram_task_create_many`: creates multiple tasks in one batch operation.
  * `engram_task_update`: modifies properties of a task.
  * `engram_task_note_append`: appends a timestamped log note to a task's evidence.
  * `engram_task_start`: transitions a task to `in_progress`.
  * `engram_task_done`: transitions a task to `done` with evidence.
  * `engram_task_block`, `engram_task_unblock`, `engram_task_cancel`, `engram_task_retire`: lifecycle maintenance helpers.
* Memory tools:
  * `engram_memory_list`: lists memories for the active project using the shared list envelope.
  * `engram_memory_get`: retrieves a memory by id.
  * `engram_memory_create`: creates a memory from normal user-facing fields.
  * `engram_memory_update`: updates a memory by id.
  * `engram_memory_update_many`: updates multiple memories in one batch operation.
  * `engram_memory_delete`: deletes a memory by id.
  * `engram_memory_delete_many`: deletes multiple memories in one batch operation.
  * `engram_memory_search`: runs FTS5 plus semantic hybrid query search over all project memories.
* Phase tools:
  * `engram_phase_list`: lists all milestone phases for the project in priority order.
  * `engram_phase_create`: creates a new first-class project phase milestone.
  * `engram_phase_start`: activates a specific phase, demoting all other project phases to planned.
  * `engram_phase_complete`: marks a `review_pending` milestone phase as complete with evidence.
  * `engram_phase_update`: updates mutable phase metadata.
  * `engram_phase_cancel`: cancels a phase after lifecycle safety checks.
  * `engram_phase_archive`: archives a terminal phase after lifecycle safety checks.

---

## 3. Recommended Agent Workflow

An AI agent connected to the Engram MCP server should follow this structured loop:

### Step 1: Initialize Workspace
The developer initializes the project once:
```bash
engram init --name "my-app"
```

### Step 2: Session Startup and Claiming Work
At the beginning of each session, the agent calls `engram_workflow_start`.
- If a task is already `in_progress`, the agent resumes it.
- If no task is active, the agent claims the highest-priority open task, checks out its target branch, and retrieves the packed context.
- If the task is phased, the branch should follow `feat/<plan_key>-<phase_key>`.
- If the task is intentionally unphased, the fallback branch is `feat/misc`.
- If no tasks exist, the agent prompts the developer or uses `engram_task_create` to define the first task.

When creating tasks from implementation phase documents, use the Task Decomposition Skill guidance at `docs/skills/task-decomposition.md` to avoid weak title-only tasks and ensure execution-ready metadata.

For non-trivial tasks, write the per-task plan at `.engram/task-plans/<plan_key>/<phase_key>/<task_key>/task-plan.md` before coding.

### Step 3: Deep Context Retrieval
If the agent needs deep constraints or related documentation for a task, it reads the resource `engram://task/{task_id}/context`.

### Step 4: Iterative Development
During the coding phase, the agent implements the scoped task and records diagnostic evidence as needed:
- Call `engram_task_note_append` to record implementation or migration progress.
- Use `engram_memory_create` when a durable decision, lesson, or constraint should be captured.

### Step 5: Verification and Session Completion
When the implementation is complete and verified:
- Call `engram_workflow_verify` to run the repo-local verification checks.
- Call `engram_workflow_finish_and_commit` to commit and push already-staged verified changes.
- If the last unfinished task in a phase was completed, the phase moves to `review_pending`.
- Phase review is then completed with `engram_phase_complete` after durable lessons and decisions are curated.

### Step 6: Phase-Level Memory Review
During phase completion, review durable lessons and decisions using memory CRUD plus batch helpers (`engram_memory_list`, `engram_memory_get`, `engram_memory_create`, `engram_memory_update`, `engram_memory_delete`, `engram_memory_update_many`, `engram_memory_delete_many`) before running `engram_phase_complete`. Only complete a phase after it has reached `review_pending`.

---

## 4. Troubleshooting

### Error: `PROJECT_NOT_BOUND`
* Cause: The workspace directory from which the MCP server or agent was launched has not been initialized.
* Solution: Open a terminal in the target repository root and run `engram init --name "<project-name>"`.

### Error: Missing optional MCP dependencies
* Cause: Engram was installed without the fast STDIO server dependencies.
* Solution: Reinstall the package using the MCP extra: `uv pip install -e ".[mcp]"`.

### FTS5 Lexical Search Returns No Results
* Cause: The search query is too specific or uses common SQL reserved characters.
* Solution: Simplify query terms or call `engram_memory_search` with standard alphanumeric strings.
