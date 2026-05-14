# Engram User Manual

Engram is a local-first, agent-agnostic persistent memory system designed to help AI agents (and human developers) maintain state and context across multiple sessions.

---

## 1. Core Concepts

### Projects
A **Project** is the top-level container. It maps a local repository (via `.git` root) to a structured entry in the Engram database.
- Every command is project-aware based on your current working directory.

### Tasks
**Tasks** are the units of work. They have status, priority, and fields for tracking evidence and acceptance criteria.
- Lifecycle: `todo → in-progress → done | blocked | cancelled`
- Tasks allow agents to break down complex goals into manageable steps.

### Sessions
A **Session** is a work checkpoint. Closing a session records a summary and next steps, which are surfaced in the next `context startup` call — this is the core resumability mechanism.
- `session start` is optional for humans who want explicit goal-setting.
- `session close` is always safe to call — it auto-creates a session if none is open.

### Memories
**Memories** are key pieces of information, decisions, or architectural notes that should persist beyond a single task.
- They are searchable via Full-Text Search (FTS5) with relevance ranking.
- Memories with `always_include=true` appear in every startup context.

---

## 2. Command Reference

### Initialization
- `engram init`: Set up the current directory as an Engram project.
  - `--name`: Human-readable name.
  - `--id`: Unique project slug.
  - `--summary`: Brief description.

### Context Generation (Agent Essentials)
- `engram context startup`: The first command an agent should run. Shows project summary, last checkpoint, active tasks, and key memories.
- `engram context task <task_id>`: Provides deep context on a specific task, including history and evidence.

### Task Management
- `engram task list`: View all tasks for the current project.
- `engram task next`: Get the single highest-priority `todo` task. Use this instead of scanning `task list`.
- `engram task add "<Title>"`: Create a new task.
- `engram task update <task_id> --field <field> --value <value>`: Update task details.
  - Common fields: `status`, `priority`, `description`, `acceptance`, `evidence`, `phase`, `tags`.
  - Statuses: `todo`, `in-progress`, `done`, `blocked`, `cancelled`.
  - Priorities: `low`, `medium`, `high`, `critical`.
- `engram task done <task_id> --evidence "<text>"`: Mark a task done and record evidence in one command.
- `engram task note <task_id> "<note>"`: Append a timestamped note to a task's evidence log (non-destructive).
- `engram task get <task_id>`: View full details of a task.

### Session Management
- `engram session list`: View all sessions (full history).
- `engram session list --active`: Show only open sessions.
- `engram session start --goal "<goal>"`: (Optional) Start a session with an explicit goal.
- `engram session close --summary "<text>" --next-steps "<text>"`: Finalize your work and create a checkpoint. Safe to call even with no active session.

### Memory Management
- `engram memory add "<Title>" --content "<Content>"`: Store a key decision or fact.
- `engram memory search "<query>"`: Find relevant memories (FTS5, ranked by relevance).
- `engram memory list`: List all memories.
- `engram memory get <memory_id>`: View full memory details.

### Exporting
- `engram export snapshot`: Generates a Markdown report of the entire project state.
- `engram export handoff`: Generates a focused Markdown file optimized for the next agent turn.

### Help
- `engram guide`: Show this manual (works from any directory).
- `engram guide <section>`: Show a specific section (`concepts`, `commands`, `workflow`, `troubleshooting`).

---

## 3. Recommended Agent Workflow

To maintain perfect context, agents should follow this standard loop:

### Step 1: Startup
Always run `engram context startup` to understand where you are. The output includes the last checkpoint, active tasks, and pinned constraints.

### Step 2: Task Selection
1. Run `engram task next` to get the highest-priority task automatically.
2. Run `engram task update <id> --field status --value in-progress` to claim it.
3. If no task exists, use `engram task add` to create one.

### Step 3: Execution
- Perform the work.
- Use `engram task note <id> "<note>"` to log progress without overwriting evidence.
- If you make a significant decision, run `engram memory add`.
- If you hit a blocker, update the task status to `blocked`.

### Step 4: Completion & Handoff
1. Run `engram task done <id> --evidence "<what proves it's done>"`.
2. Run `engram session close --summary "<what was done>" --next-steps "<what's next>"`.
3. (Optional) Run `engram export handoff` to provide a clean state for human review.

---

## 4. Troubleshooting

### Command Failures
- **"No such option: --status"**: Use `--field status --value <status>` with `task update` instead.
- **"Project not found"**: Ensure you are in a directory initialized with `engram init`.
- **`task next` returns nothing**: All tasks are in `done`/`blocked`/`cancelled`. Use `task list` to review.

### Stuck?
If `--help` doesn't explain a behavior, run `engram guide <section>` for this manual from any directory.
