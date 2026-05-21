# Engram User Manual

Engram is a local-first, agent-agnostic persistent memory system designed to help AI agents (and human developers) maintain state and context across multiple sessions.

---

## 1. Core Concepts

### Projects
A **Project** is the top-level container. It maps a local repository to a structured entry in the Engram database.
- Every command is project-aware based on your **current working directory**.
- The database lives globally at `~/.engram/memory.db` — not in your repo. Memory survives repo moves and deletes.

### Tasks
**Tasks** are the units of work within a project.
- **Lifecycle:** `todo → in-progress → done | blocked | cancelled`
- **Priority levels:** `low | medium | high | critical`
- Fields: `title`, `description`, `acceptance`, `evidence`, `phase`, `tags`
- Use `task next` to get the highest-priority `todo` task automatically — do not scan `task list` manually.

### Sessions
A **Session** is a work checkpoint. Closing a session records a summary and next steps, which are surfaced in the next `context startup` call — this is the core resumability mechanism.
- `session start` is optional. It lets you set an explicit goal for the session.
- `session close` is always safe to call — it auto-creates a session if none is open.
- `--summary` is **required** on `session close`. It must be passed as a flag, not entered interactively.

### Memories
**Memories** are key facts, decisions, lessons, or constraints that should persist beyond a single task.
- **Types:** `note | decision | lesson | constraint | snippet`
- Searchable via Full-Text Search (FTS5) with relevance ranking.
- Memories with `--always-include` appear in every `context startup` call — use for hard constraints.
- `--content` is **required** on `memory add`. It must be passed as a flag, not entered interactively.

---

## 2. Command Reference

### Initialization

```
engram init [--name NAME] [--id ID] [--summary SUMMARY]
```
Register the current directory as an Engram project. Creates the project if it doesn't exist, or binds the current directory to an existing project with the same ID.

---

### Context Generation

```
engram context startup
```
The **first command** an agent should run every session. Returns: project summary, last session checkpoint (done/next), active tasks, and always-include memories. Target: < 500 tokens.

```
engram context task <task_id>
```
Deep context on a specific task: description, acceptance criteria, and linked memories. Use after `task next` when you need full detail.

---

### Task Management

```
engram task next
```
Returns the single highest-priority `todo` task (critical > high > medium > low, then oldest first). Use this instead of scanning `task list`. If empty, the current phase has no tasks — use `task add`.

```
engram task list [--status STATUS]
```
List all tasks for the project. Optionally filter by status: `todo`, `in-progress`, `done`, `blocked`, `cancelled`.

```
engram task add "<Title>" [--description TEXT] [--priority PRIORITY]
                          [--status STATUS] [--phase TEXT]
                          [--acceptance TEXT] [--tags tag1,tag2]
```
Create a new task. Defaults: `priority=medium`, `status=todo`.

```
engram task start <task_id>
```
Mark a task as `in-progress` (shorthand for claiming a task). Use immediately after `task next`.

```
engram task update <task_id> --field <field> --value <value>
```
Update a single field on a task.

Valid fields and their allowed values:

| Field | Allowed Values |
|:------|:--------------|
| `status` | `todo`, `in-progress`, `done`, `blocked`, `cancelled` |
| `priority` | `low`, `medium`, `high`, `critical` |
| `title` | Any string |
| `description` | Any string |
| `acceptance` | Any string |
| `evidence` | Any string |
| `phase` | Any string |
| `tags` | Comma-separated: `tag1,tag2` |

Passing an unknown field or invalid status/priority value returns an error.

```
engram task done <task_id> --evidence "<proof>"
```
Atomically marks a task `done` and records evidence. `--evidence` is strongly recommended — include test results and commit hash.

```
engram task note <task_id> "<note>"
```
Append a timestamped note to a task's evidence log without overwriting existing entries. Safe to call multiple times during work.

```
engram task get <task_id>
```
Show full details of a task: all fields, evidence log, and tags.

---

### Session Management

```
engram session start [--goal "GOAL"]
```
(Optional) Start a session with an explicit goal. Useful for human developers; agents can skip this.

```
engram session close --summary "SUMMARY" [--next-steps "NEXT"]
```
Close the active session and create a checkpoint. `--summary` is **required**. Safe to call even with no active session open — auto-creates one if needed.

```
engram session list [--active]
```
List all sessions. Use `--active` to show only open sessions.

---

### Memory Management

```
engram memory add "<Title>" --content "CONTENT" [--type TYPE]
                            [--tags tag1,tag2] [--always-include]
```
Store a key decision, lesson, or constraint. `--content` is **required**.

Valid types: `note` (default), `decision`, `lesson`, `constraint`, `snippet`.

Use `--always-include` for hard constraints that must appear in every startup context.

```
engram memory search "<query>" [--type TYPE] [--tag TAG]
```
Full-text search across memories (FTS5, relevance-ranked). Optionally filter by type or tag.

```
engram memory list
```
List all memories for the current project (ID, title, type, tags).

```
engram memory get <memory_id>
```
Show full details of a memory including content.

```
engram memory update <memory_id> --field <field> --value <value>
```
Update a memory field. Valid fields: `title`, `content`, `type`, `tags`, `always_include`.

```
engram memory delete <memory_id> [-y]
```
Delete a memory. Prompts for confirmation unless `-y` is passed.

---

### Project Management

```
engram project get
```
Show current project details (ID, name, status, summary, repo paths).

```
engram project update [--name NAME] [--summary SUMMARY] [--status STATUS]
```
Update project metadata. Valid statuses: `active`, `paused`, `archived`.

```
engram project list
```
List all registered Engram projects across all repos.

---

### Exporting

```
engram export snapshot [--output FILE]
```
Export a full project snapshot to Markdown (default: `SNAPSHOT.md`). Includes all tasks, memories, and session history.

```
engram export handoff [--output FILE]
```
Export a focused handoff document (default: `HANDOFF.md`). Optimised for the next agent turn — active tasks, critical context, next steps.

---

### Help

```
engram guide [SECTION]
```
Show this manual from any directory. Optional sections: `concepts`, `commands`, `workflow`, `troubleshooting`.

---

## 3. Recommended Agent Workflow

### Step 1: Startup
```
engram context startup
```
Understand the project state: last checkpoint, active tasks, pinned constraints.

### Step 2: Claim a Task
```
engram task next             → get the highest-priority todo task
engram task start <id>       → mark it in-progress
engram context task <id>     → get full detail if needed
```
If `task next` returns nothing — the current phase has no tasks yet. Run `engram task add` or ask the user to define the next phase.

### Step 3: Do the Work
```
engram task note <id> "<note>"            → log progress non-destructively
engram memory add "<title>" --content ... → record decisions or lessons learned
engram task update <id> --field status --value blocked  → if you hit a blocker
```

### Step 4: Commit & Close
```
# Quality gate first
uv run ruff check . --fix && uv run pytest tests/ -v

# Commit
git add -A && git commit -m "type(scope): description [task-id]"
git push origin feat/<task-id>-<slug>

# Close in Engram
engram task done <id> --evidence "pytest: X passed, commit: <hash>"
engram session close --summary "<what was done>" --next-steps "<what's next>"
```

---

## 4. Troubleshooting

### `Error: Missing option '--summary'`
`session close` requires `--summary` as a flag — it no longer prompts interactively.
```
engram session close --summary "What I did" --next-steps "What's next"
```

### `Error: Missing option '--content'`
`memory add` requires `--content` as a flag — it no longer prompts interactively.
```
engram memory add "My Memory" --content "The content here"
```

### `Error: Unknown field '...'`
`task update` and `memory update` validate field names. Run `engram guide commands` to see valid fields.

### `Error: Invalid status '...'`
Valid task statuses: `todo`, `in-progress`, `done`, `blocked`, `cancelled`. Note: `completed` is not valid — use `done`.

### `task next` returns nothing
All tasks are in a terminal state (`done`, `blocked`, `cancelled`). Either:
- Run `engram task list` to review the full state.
- Run `engram task add "<Next Task>"` to create the next phase of work.

### `Error: Project not found`
You are not in a directory registered with Engram. Run `engram init` or `cd` to the correct project root.

### Stuck?
Run `engram guide <section>` for this manual from any directory.
Run `engram <command> --help` for flag-level help on any specific command.
