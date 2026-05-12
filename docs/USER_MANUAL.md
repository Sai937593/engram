# Engram User Manual

Engram is a local-first, agent-agnostic persistent memory system designed to help AI agents (and human developers) maintain state and context across multiple sessions.

---

## 1. Core Concepts

### Projects
A **Project** is the top-level container. It maps a local repository (via `.git` root) to a structured entry in the Engram database.
- Every command is project-aware based on your current working directory.

### Tasks
**Tasks** are the units of work. They have status (backlog, in_progress, completed, etc.), priority, and fields for tracking evidence and acceptance criteria.
- Tasks allow agents to break down complex goals into manageable steps.

### Sessions
A **Session** represents a single interaction or "turn" of work.
- Sessions group tasks and memories created during that time.
- Closing a session generates a summary and next steps, which are preserved for the next agent.

### Memories
**Memories** are key pieces of information, decisions, or architectural notes that should persist beyond a single task.
- They are searchable via Full-Text Search (FTS5).

---

## 2. Command Reference

### Initialization
- `engram init`: Set up the current directory as an Engram project.
  - `--name`: Human-readable name.
  - `--id`: Unique project slug.
  - `--summary`: Brief description.

### Context Generation (Agent Essentials)
- `engram context startup`: The first command an agent should run. It provides the project summary and active tasks.
- `engram context task <task_id>`: Provides deep context on a specific task, including history and evidence.

### Task Management
- `engram task list`: View all tasks for the current project.
- `engram task add "<Title>"`: Create a new task.
- `engram task update <task_id> --field <field> --value <value>`: Update task details.
  - Common fields: `status`, `priority`, `description`.
  - Common statuses: `backlog`, `in_progress`, `completed`, `blocked`.
- `engram task get <task_id>`: View full details of a task.

### Session Management
- `engram session list`: View recent work history.
- `engram session close`: Finalize your work.
  - This command prompts for a summary of what was done and what should be done next.
  - **Crucial for agent handoffs.**

### Memory Management
- `engram memory add "<Title>" --content "<Content>"`: Store a key decision or fact.
- `engram memory search "<query>"`: Find relevant information across the project history.
- `engram memory list`: List all memories.

### Exporting
- `engram export snapshot`: Generates a Markdown report of the entire project state.
- `engram export handoff`: Generates a focused Markdown file optimized for the next agent turn.

---

## 3. Recommended Agent Workflow

To maintain perfect context, agents should follow this standard loop:

### Step 1: Startup
Always run `engram context startup` to understand where you are.

### Step 2: Task Selection
1. Run `engram task list` to see what needs to be done.
2. If a task exists, run `engram task update <id> --field status --value in_progress`.
3. If no task exists, ask the user or use `engram task add` to create one.

### Step 3: Execution
- Perform the work.
- If you make a significant decision, run `engram memory add`.
- If you hit a blocker, update the task status to `blocked`.

### Step 4: Completion & Handoff
1. Mark the task as `completed`.
2. Run `engram session close --summary "Implemented X" --next-steps "Do Y"`.
3. (Optional) Run `engram export handoff` to provide a clean state for the next turn.

---

## 4. Troubleshooting

### Command Failures
- **"No such option: --status"**: Use `--field status --value <status>` instead.
- **"Project not found"**: Ensure you are in a directory initialized with `engram init`.

### Stuck?
If `--help` doesn't explain a behavior, refer to this manual first before asking the user.
Avoid dumping this entire manual into your context; search for specific sections if needed.
