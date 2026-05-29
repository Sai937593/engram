# Engram User Manual

Engram is a local-first, agent-agnostic persistent memory system for AI coding assistants and developers. It stores durable project context in a central SQLite database (`~/.engram/memory.db`) and exposes it programmatically through a custom Model Context Protocol (MCP) server, alongside a minimal companion CLI for workspace management.

---

## 1. Core Concepts

### Projects
A project binds one or more local repository absolute paths to a unique database record. When the MCP server or CLI is invoked, it dynamically resolves the active project using the current working directory. Memory and task states live globally outside the repository, surviving branch checkouts, resets, and folder moves.

### Phases
Phases are first-class project milestones that group related tasks.
- **Planning structure:** `Project -> Phase -> Task`
- **Lifecycle:** `planned -> active -> done | blocked | cancelled`
- Only one phase is active per project. Activating a phase automatically demotes all other phases in the same project back to `planned`.

### Tasks
Tasks are specific actionable units of work.
- **Lifecycle:** `todo -> in-progress -> done | blocked | cancelled`
- **Priority levels:** `low | medium | high | critical`
- **Metadata:** `title`, `description`, `acceptance`, `evidence`, `phase_id`, `tags`, `depends_on`, `relevant_files`.
- Agents automatically resolve task context and associated dependencies programmatically.

### Memories
Memories are persistent facts designed to survive across coding sessions.
- **Types:** `note`, `decision`, `lesson`, `constraint`, `snippet`
- **Retrieval:** Automatically indexed via SQLite FTS5 lexical search combined with local fastembed semantic search.
- **Guardrails:** Pinned policy memories (levels L0/L1) act as active agent constraints and are automatically injected into the agent's startup context.

---

## 2. Command Reference

### Companion CLI Reference
The Engram command-line interface has been trimmed to three essential workspace setup and utility commands:

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
Utility command to print the absolute path, disk size, and SQLite integrity connection status of the global database at `~/.engram/memory.db`.

### Deprecated & Removed CLI Commands
To preserve clean separation of concerns and maintain a single source of truth, **all programmatic memory, task, phase, and workflow management commands have been removed from the CLI**. All agent interactions must go through the MCP server.

Refer to the table below to transition from the old CLI commands to their MCP server equivalents:

| Deprecated CLI Command | Status | MCP Server Equivalent |
| :--- | :--- | :--- |
| `engram context startup` | **REMOVED** | Read resource `engram://startup` |
| `engram context task <id>` | **REMOVED** | Read resource `engram://task/{task_id}/context` |
| `engram start` | **REMOVED** | Call tool `engram_workflow_start` |
| `engram finish` | **REMOVED** | Call tool `engram_workflow_finish` |
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
    *   `engram_workflow_finish`: Stage changes, execute validation tests, confirm Conventional Commit, commit, and mark task done.
*   **Task Management:**
    *   `engram_task_list`: Filters and lists project tasks by status or phase.
    *   `engram_task_get`: Retrieves full details of a specific task.
    *   `engram_task_next`: Returns the highest-priority actionable `todo` task.
    *   `engram_task_create`: Creates a new project task.
    *   `engram_task_update`: Modifies properties of a task.
    *   `engram_task_note_append`: Appends a timestamped log note to a task's evidence.
    *   `engram_task_start`: Transition task status to `in-progress`.
    *   `engram_task_done`: Transition task status to `done` with evidence.
*   **Memory Management:**
    *   `engram_memory_create`: Creates a persistent project memory (accepts `title`, `content`, `type`, `scope`, `level`).
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

### Step 3: Deep Context Retrieval
If the agent needs deep constraints or related documentation for a task, it reads the resource:
`engram://task/{task_id}/context`

### Step 4: Iterative Development & Memory Capture
During the coding phase, the agent captures critical software engineering decisions, lessons, or constraints:
*   Calls `engram_memory_create` to log decisions (e.g. why a specific architecture or library was selected).
*   Calls `engram_task_note_append` to record diagnostic evidence or migration progress.

### Step 5: Verification & Session Completion
When the implementation is complete and verified:
*   The agent calls `engram_workflow_finish` to stage changes, execute validation tests, confirm the Conventional Commit message, and push the branch.

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
