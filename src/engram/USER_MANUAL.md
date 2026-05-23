# Engram User Manual

Engram is a local-first, agent-agnostic memory system for AI coding assistants and developers. It stores durable project context in `~/.engram/memory.db` and exposes it through a compact CLI.

## 1. Core Concepts

### Projects

A project maps one or more local repository paths to a record in the Engram database.

- Commands are project-aware based on the current working directory.
- Memory lives outside the repository, so it survives branch changes, moves, and deletes.

### Tasks

Tasks are units of work within a project.

- Lifecycle: `todo -> in-progress -> done | blocked | cancelled`
- Priority levels: `low | medium | high | critical`
- Important fields: `title`, `description`, `acceptance`, `evidence`, `phase`, `phase_id`, `tags`, `depends_on`
- Use `engram task next` or `engram start` to claim work instead of scanning all tasks manually.

### Memories

Memories are durable facts that should survive a single coding session.

- Types: `note`, `decision`, `lesson`, `constraint`, `snippet`
- Searchable through SQLite FTS5.
- Memories marked `--always-include` appear in startup context.
- Constraints, decisions, and lessons are always included by their typed helper commands.

### Workflow State

Engram uses task state, evidence, notes, and memories as the durable handoff mechanism. `engram context startup` summarizes the project state for the next agent turn, and exports can produce Markdown snapshots or handoffs when needed.

## 2. Command Reference

### Initialization

```bash
engram init [--name NAME] [--id ID] [--summary SUMMARY]
```

Register the current directory as an Engram project. If the project already exists, Engram binds the current path to it.

### Context

```bash
engram context startup
```

Generate compact startup context for an agent: project summary, active tasks, and pinned memories.

```bash
engram context task <task_id>
```

Generate deeper context for one task, including description, acceptance criteria, dependencies, and relevant project knowledge.

### Task Management

```bash
engram task next
```

Show the highest-priority actionable `todo` task.

```bash
engram task list [--status STATUS] [--all] [--phase TEXT]
```

List tasks for the current project. By default, Engram shows `todo` tasks; use `--all` to include terminal states.
- `--phase TEXT`: Filter tasks to a first-class phase ID or unique phase title (matches legacy free-form phase text if no first-class phase matches).

```bash
engram task add "<Title>" [--description TEXT] [--priority PRIORITY]
                          [--status STATUS] [--phase TEXT]
                          [--acceptance TEXT] [--tags tag1,tag2]
                          [--depends-on TASK_IDS]
```

Create a task in the current project. Defaults are `priority=medium` and `status=todo`.
- `--phase TEXT`: Associate the task with a phase. If `TEXT` matches a first-class phase ID or unique title, the task's first-class `phase_id` and legacy `phase` fields are resolved and set. If no first-class phase matches, it falls back to storing the free-form legacy text in `phase`.

```bash
engram task start <task_id>
```

Mark a task as `in-progress`.

```bash
engram task update <task_id> --field <field> --value <value>
```

Update a single task field.
- **Valid Fields:** `title`, `status`, `priority`, `description`, `acceptance`, `tags`, `phase`, `phase_id`, `evidence`, `depends_on`.
- **Phase association (`phase_id`):** Update the `phase_id` field with a first-class phase ID or unique title. This resolves the phase, links the task to it, and mirrors the title into the legacy `phase` text field for compatibility.
- **Legacy phase title (`phase`):** Update the `phase` field directly with a text string to use legacy free-form phase labels without establishing a first-class phase link.
- **Clearing a task's phase:** Set `--field phase_id --value none` (or `null`/`clear`) to clear both `phase_id` and `phase` fields, dissociating the task from any phase.

```bash
engram task note <task_id> "<note>"
```

Append a timestamped note to a task's evidence log.

```bash
engram task done <task_id> --evidence "<proof>"
```

Mark a task done and record completion evidence.

```bash
engram task get <task_id>
```

Show full task details.

### Memory Management

```bash
engram memory add "<Title>" --content "CONTENT" [--type TYPE]
                            [--tags tag1,tag2] [--always-include]
```

Store a note, decision, lesson, constraint, or snippet.

```bash
engram memory search "<query>" [--type TYPE] [--tag TAG]
engram memory list
engram memory get <memory_id>
engram memory update <memory_id> --field <field> --value <value>
engram memory delete <memory_id> [-y]
```

Search, list, inspect, update, or delete project memories.

### Typed Memory Helpers

```bash
engram decision add "<title>" --content "<rationale>"
engram lesson add "<title>" --content "<what was learned>"
engram constraint add "<title>" --content "<rule and reason>"
engram snippet add "<title>" --content "<reusable command or code>"
```

Each typed helper also supports `list`, `get`, and `search`.

### Project Management

```bash
engram project get
engram project update [--name NAME] [--summary SUMMARY] [--status STATUS]
engram project list
```

Inspect or update project metadata. Valid statuses are `active`, `paused`, and `archived`.

### Phase Management

```bash
engram phase add "<Title>" [--description TEXT] [--status STATUS]
                         [--acceptance TEXT] [--order-index INTEGER]
```

Add a phase to the current project. The default status is `planned`. Valid statuses are `planned`, `active`, `done`, `blocked`, and `cancelled`.

```bash
engram phase list
```

List all phases for the current project.

```bash
engram phase get <phase_ref>
```

Show full details for a phase by ID or unique title.

```bash
engram phase start <phase_ref>
```

Start a phase by ID or unique title and make it the only active phase. Any other active phase in the project is automatically set back to `planned`.

```bash
engram phase update <phase_ref> --field <field> --value <value>
```

Update a mutable phase field by ID or unique title. Common fields are `title`, `description`, `status`, `acceptance`, and `order_index`.

```bash
engram phase done <phase_ref> --evidence "<proof>" [--force]
```

Mark a phase as done with completion evidence. This requires completing all linked tasks, unless `--force` is provided to override the completion guard.

### Exports

```bash
engram export snapshot [-o FILE]
engram export handoff [-o FILE]
```

Create Markdown exports for full snapshots or focused handoffs.

### Workflow Commands

```bash
engram start
```

Claim the next task and switch to the appropriate phase branch when needed.

```bash
engram finish [--type TYPE]
```

Finish the active task by committing, pushing, and marking the task done. Use `--type` for the Conventional Commit type when Engram cannot infer one.

```bash
engram commit "type(scope): subject [task-id]"
```

Stage all files, validate the Conventional Commit message, and commit.

### Help

```bash
engram guide [SECTION]
engram <command> --help
```

Show the packaged manual or command-specific help.

## 3. Recommended Agent Workflow

### Step 1: Startup

```bash
engram context startup
```

Read current project state, active work, and pinned constraints.

### Step 2: Claim Work

```bash
engram start
engram context task <id>
```

Use `engram task add` if `engram start` reports that no tasks are defined.

### Step 3: Work and Capture Knowledge

```bash
engram task note <id> "<progress note>"
engram decision add "<title>" --content "<why>"
engram lesson add "<title>" --content "<how it was solved>"
engram constraint add "<title>" --content "<rule and reason>"
engram snippet add "<title>" --content "<reusable command>"
```

If work is blocked:

```bash
engram task update <id> --field status --value blocked
engram task note <id> "<blocker details>"
```

### Step 4: Validate and Finish

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/ -v
engram finish --type <feat|fix|docs|chore>
```

## 4. Troubleshooting

### `Error: Missing option '--content'`

`memory add` and typed memory add commands require content as a flag.

```bash
engram memory add "My Memory" --content "The content here"
```

### `Error: Unknown field '...'`

`task update` and `memory update` validate field names. Run `engram task update --help` or `engram memory update --help`.

### `Error: Invalid status '...'`

Valid task statuses are `todo`, `in-progress`, `done`, `blocked`, and `cancelled`. Use `done`, not `completed`.

### `task next` returns nothing

All tasks are in a terminal state or no tasks exist. Use:

```bash
engram task list --all
engram task add "<Next Task>"
```

### `Error: Project not found`

You are not in a directory registered with Engram. Run `engram init` from the repository root or change to a registered directory.
