# Engram User Manual

Engram is a local-first, agent-agnostic memory system for AI coding assistants and developers. It stores durable project context in `~/.engram/memory.db` and exposes it through a compact CLI.

## 1. Core Concepts

### Projects

A project maps one or more local repository paths to a record in the Engram database.

- Commands are project-aware based on the current working directory.
- Memory lives outside the repository, so it survives branch changes, moves, and deletes.

### Phases

Phases are first-class project milestones that group related tasks.

- Planning structure: `Project -> Phase -> Task`
- Lifecycle: `planned -> active -> done | blocked | cancelled`
- Only one phase should be active per project. `engram phase start <phase_ref>` activates one phase and demotes any other active phase in the same project back to `planned`.
- New task workflows should use first-class phase links through `phase_id`.

### Tasks

Tasks are units of work within a project.

- Lifecycle: `todo -> in-progress -> done | blocked | cancelled`
- Priority levels: `low | medium | high | critical`
- Important fields: `title`, `description`, `acceptance`, `evidence`, `phase_id`, `phase`, `tags`, `depends_on`, `relevant_files`
- `phase_id` is the first-class phase association. The legacy free-form `phase` text remains readable during compatibility and is backfilled into first-class phases during database initialization when possible.
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

Generate compact startup context for an agent: project summary, active task/phase, task-relevant file path hints (when present), L0/L1 project guardrails, and task memory candidates.

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

List tasks. By default, Engram shows todo tasks; use `--all` to include terminal states. Use `--phase TEXT` to filter by first-class phase ID or unique phase title.

```bash
engram task add "<Title>" [--description TEXT] [--priority PRIORITY]
                          [--status STATUS] [--phase TEXT]
                          [--acceptance TEXT] [--tags tag1,tag2]
                          [--depends-on TASK_IDS] [--files path1,path2]
```

Create a task. Defaults are `priority=medium` and `status=todo`. If `--phase` matches a first-class phase ID or unique title, Engram stores the linked `phase_id` and mirrors the phase title into legacy `phase` for compatibility. If no first-class phase matches, the value is stored as legacy free-form phase text.
- `--files path1,path2`: Optional task-scoped relevant file path hints. Startup and task context display paths only (no file contents).

```bash
engram task start <task_id>
```

Mark a task as `in-progress`.

```bash
engram task update <task_id> --field <field> --value <value>
```

Update a single task field. Common fields are `status`, `priority`, `title`, `description`, `acceptance`, `evidence`, `phase_id`, `phase`, `tags`, and `depends_on`.

- Use `--field phase_id --value <phase_id_or_unique_title>` to link a task to a first-class phase.
- Use `--field phase_id --value none` to clear both `phase_id` and legacy `phase`.
- `--field phase` is compatibility-aware: if the value matches a first-class phase ID/title, Engram updates `phase_id` and `phase`; otherwise it stores free-form legacy text in `phase` and clears `phase_id`.

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

```bash
engram task files list <task_id>
engram task files add <task_id> --files path1,path2
engram task files remove <task_id> --files path1,path2
```

List, append, or remove task relevant file path hints without changing other task fields.

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

### Guardrail Controls

```bash
engram guardrail demote <memory_id> --reason "<reason>"
```

Demote a project-scope guardrail by exactly one level (`L0 -> L1`, `L1 -> L2`, `L2 -> L3`). `L3` guardrails cannot be demoted further, and a non-empty reason is required.

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

List phases for the current project in `order_index` order.

```bash
engram phase get <phase_ref>
```

Show full details for a phase by ID or unique title.

```bash
engram phase start <phase_ref>
```

Start a phase by ID or unique title and make it the only active phase in the project.

```bash
engram phase update <phase_ref> --field <field> --value <value>
```

Update a mutable phase field. Supported fields are `title`, `description`, `status`, `order_index`, `acceptance`, and `evidence`.

```bash
engram phase done <phase_ref> --evidence "<proof>" [--force]
```

Mark a phase as done with completion evidence. By default, Engram rejects completion while linked `todo`, `in-progress`, or `blocked` tasks remain; use `--force` only when intentionally closing with unfinished linked work.

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
