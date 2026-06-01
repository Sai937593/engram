# Engram User Manual

Engram is a local-first, agent-agnostic persistent memory system for AI coding assistants and developers. It stores durable project context in a repo-local SQLite database (`.engram/memory.db`) and exposes it programmatically through a custom Model Context Protocol (MCP) server, alongside a trimmed companion CLI for optional human setup and diagnostics.

---

## 1. Core Concepts

### Projects
A project maps to repo-local Engram state rooted in the current repository. When the MCP server or CLI utility commands are invoked from that workspace, Engram resolves the active project using the current working directory. Memory and task state are persisted in `.engram/memory.db` inside the repository.

### Phases
Phases are first-class project milestones that group related tasks.
- **Planning structure:** `Project -> Phase -> Task`
- **Lifecycle:** `planned -> active -> done | blocked | cancelled`
- Only one phase is active per project. Activating a phase automatically demotes all other phases in the same project back to `planned`.

### Tasks
Tasks are specific actionable units of work.
- **Lifecycle:** `draft -> ready -> in-progress -> done | blocked | cancelled`
- **Priority levels:** `low | medium | high | critical`
- **Metadata:** `title`, `description`, `acceptance`, `evidence`, `phase_id`, `tags`, `depends_on`, `relevant_files`.
- Agents automatically resolve task context and associated dependencies programmatically.

### Memories
Memories are persistent facts designed to survive across coding sessions.
- **Normal interface:** Use memory CRUD (`list`, `get`, `create`, `update`, `delete`) for routine work.
- **Retrieval:** Automatically indexed via SQLite FTS5 lexical search combined with local fastembed semantic search.
- **Historical/internal detail:** Legacy lifecycle fields (for example levels, scope, tags, always_include, type-specific governance) may exist in stored schema or migration history, but are not part of normal agent workflow guidance.

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
Opens this interactive user manual directly in the terminal, rendered as beautifully formatted rich Markdown.

#### `engram db`
```bash
engram db
```
Utility command to print the absolute path, disk size, and SQLite integrity connection status of the repo-local database for the current workspace.

### Deprecated & Removed CLI Commands
To preserve clean separation of concerns and maintain a single source of truth, **all programmatic memory, task, phase, and workflow management commands have been removed from the CLI**. All agent interactions must go through the MCP server.

Refer to the table below to transition from the old CLI commands to their MCP server equivalents:

| Deprecated CLI Command | Status | MCP Server Equivalent |
| :--- | :--- | :--- |
| `engram context startup` | **REMOVED** | Read resource `engram://startup` |
| `engram context task <id>` | **REMOVED** | Read resource `engram://task/{task_id}/context` |
| `engram start` | **REMOVED** | Call tool `engram_workflow_start` |
| `engram finish` | **REMOVED** | Call tool `engram_workflow_finish_and_commit` (preferred) or transitional alias `engram_workflow_finish` |
| `engram task list` | **REMOVED** | Call tool `engram_task_list` |
| `engram task get` | **REMOVED** | Call tool `engram_task_get` |
| `engram task next` | **REMOVED** | Call tool `engram_task_next` |
| `engram task add` | **REMOVED** | Call tool `engram_task_create` |
| `engram task update` | **REMOVED** | Call tool `engram_task_update` |
| `engram task note` | **REMOVED** | Call tool `engram_task_note_append` |
| `engram task done` | **REMOVED** | Call tool `engram_task_done` |
| `engram memory add` / `decision add` | **REMOVED** | Call tool `engram_memory_create` |
| `engram memory search` | **REMOVED** | Call tool `engram_memory_search` |
| `engram phase list` / `get` / `start` | **REMOVED** | Call tools `engram_phase_*` |
| `engram export snapshot` | **REMOVED** | Read resource `engram://snapshot` |
| `engram export handoff` | **REMOVED** | Read resource `engram://handoff` |

### MCP Interface Reference
Connected AI agents communicate with Engram using the standard STDIO-based Model Context Protocol.

#### Local Resources
Agents can read the following read-only Markdown resources:

*   **`engram://startup`**: Retrieves the startup context including active project details, active tasks, L0/L1 guardrails, and relevant memory candidates.
*   **`engram://task/{task_id}/context`**: Retrieves a detailed requirement context for a single task including acceptance criteria, dependencies, and relevant lessons/decisions.
*   **`engram://snapshot`**: Returns a comprehensive project summary report compiling all phases, tasks, and memories.
*   **`engram://handoff`**: Returns a focused summary of recent phase completions, active tasks, and blockers, perfect for agent handoffs.

#### Programmatic Tools
The MCP server exposes 17 tools for full interactive capabilities:

*   **Workflow Control:**
    *   `engram_workflow_start`: Starts the session workflow. Claims next actionable task, updates branch, and returns startup context.
    *   `engram_workflow_verify`: Runs local verification checks and stages changes on success.
    *   `engram_workflow_finish_and_commit`: Commits and pushes already-staged verified changes, then marks the task done.
    *   `engram_workflow_finish`: Deprecated transitional alias for `engram_workflow_finish_and_commit`.
*   **Task Management:**
    *   `engram_task_list`: Filters and lists project tasks by status or phase.
    *   `engram_task_get`: Retrieves full details of a specific task.
    *   `engram_task_next`: Returns the highest-priority actionable `ready` task.
    *   `engram_task_create`: Creates a new project task.
    *   `engram_task_update`: Modifies properties of a task.
    *   `engram_task_note_append`: Appends a timestamped log note to a task's evidence.
    *   `engram_task_start`: Transition task status to `in-progress`.
    *   `engram_task_done`: Transition task status to `done` with evidence.
*   **Memory Management:**
    *   `engram_memory_list`: Lists memories for the active project.
    *   `engram_memory_get`: Retrieves a memory by id.
    *   `engram_memory_create`: Creates a memory from normal user-facing fields (for example `title`, `content`).
    *   `engram_memory_update`: Updates a memory by id.
    *   `engram_memory_update_many`: Updates multiple memories in one batch operation.
    *   `engram_memory_delete`: Deletes a memory by id.
    *   `engram_memory_delete_many`: Deletes multiple memories in one batch operation.
    *   `engram_memory_search`: Runs FTS5 + semantic hybrid query search over all project memories.
*   **Phase Management:**
    *   `engram_phase_list`: Lists all milestone phases for the project in priority order.
    *   `engram_phase_create`: Creates a new first-class project phase milestone.
    *   `engram_phase_start`: Activates a specific phase, demoting all other project phases to planned.
    *   `engram_phase_complete`: Marks a milestone phase as complete with evidence.
*   **System Utilities:**
    *   `engram_project_current`: Returns the active project metadata resolved from the working directory.

---

## 3. Recommended Agent Workflow

An AI agent connected to the Engram MCP server should follow this structured loop:

### Step 1: Initialize Workspace
The developer initializes the project once:
```bash
engram init --name "my-app"
```

### Step 2: Session Startup & Claiming Work
At the beginning of each session, the agent calls the `engram_workflow_start` tool.
*   If a task is already `in-progress`, the agent resumes it.
*   If no task is active, the agent claims the highest priority `todo` task, checks out its target branch, and retrieves the packed context.
*   If no tasks exist, the agent prompts the developer or uses `engram_task_create` to define the first task.

When creating tasks from implementation phase documents, use the Task
Decomposition Skill guidance at `docs/skills/task-decomposition.md` to avoid
weak title-only tasks and ensure execution-ready metadata.

### Step 3: Deep Context Retrieval
If the agent needs deep constraints or related documentation for a task, it reads the resource:
`engram://task/{task_id}/context`

### Step 4: Iterative Development
During the coding phase, the agent implements the scoped task and records diagnostic evidence as needed:
*   Calls `engram_task_note_append` to record implementation or migration progress.

### Step 5: Verification & Session Completion
When the implementation is complete and verified:
*   The agent calls `engram_workflow_finish_and_commit` to commit and push already-staged verified changes.

### Step 6: Phase-Level Memory Review
During phase completion, review durable lessons and decisions using memory CRUD plus batch helpers (`engram_memory_list`, `engram_memory_get`, `engram_memory_create`, `engram_memory_update`, `engram_memory_delete`, `engram_memory_update_many`, `engram_memory_delete_many`) before running `engram_phase_complete`.

---

## 4. Troubleshooting

### Error: `PROJECT_NOT_BOUND`
*   **Cause:** The workspace directory from which the MCP server or agent was launched has not been initialized.
*   **Solution:** Open a terminal in the target repository root and run `engram init --name "<project-name>"`.

### Error: Missing optional MCP dependencies
*   **Cause:** Engram was installed without the fast STDIO server dependencies.
*   **Solution:** Reinstall the package using the MCP extra: `uv pip install -e ".[mcp]"`.

### FTS5 Lexical Search Returns No Results
*   **Cause:** The search query is too specific or uses common SQL reserved characters.
*   **Solution:** Simplify query terms or call `engram_memory_search` with standard alphanumeric strings.
