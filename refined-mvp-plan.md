# Engram — Refined MVP Plan

> This is the active plan. The original `mvp-project-plan.md` is preserved for reference.
> Last updated: 2026-05-11

---

## Decisions Summary

| # | Decision | Choice | Reason |
|:--|:---------|:-------|:-------|
| 0 | Entity philosophy | **Hybrid** — minimal types, rich metadata | Avoids 9-entity complexity without losing queryability |
| 1 | Interface | **CLI with `--json` flag** | Works with every agent; human-readable by default |
| 2 | Storage | **SQLite + generated markdown exports** | Source of truth is queryable; exports are views |
| 3 | Context packing | **Minimal startup + on-demand retrieval** | Agent pulls only what it needs |
| 4 | Entity model | **4 tables**: project, task, memory, session | Simple schema, fewer operations |
| 5 | Updates | **Field-level flags** via CLI | Precise, auditable, CLI-native |
| 6 | Session/checkpoint | **Embedded** — `session close` = checkpoint | One operation, one entity |
| 7 | Audit | **Lightweight logs** | MVP-appropriate; full audit post-MVP |
| 8 | Search | **FTS5 + tag filtering** | No dependencies, fast, good enough for scoped memory |
| 9 | Exports | **Two exports**: snapshot + handoff | Covers 95% of use cases |
| 10 | Scope | **Three levels**: global → project → task | Right granularity for the 4-table model |
| 11 | Language | **Python + click + rich** | 2 pip deps; sqlite3 is stdlib |
| 12 | Workflow | **Hybrid** — lightweight sessions, checkpoint-driven | Sessions for history, checkpoints for resumability |

---

## MVP Goal

A local CLI tool (`engram`) that gives any AI coding agent persistent, cross-session project memory with minimal context window pollution.

```text
agent starts in repo
→ engram context startup   (< 500 tokens — project + task + last checkpoint)
→ agent works, pulling details on-demand
→ engram session close     (creates checkpoint for next session)
→ next agent resumes from checkpoint
```

**Agent-provider agnostic** — works with Claude Code, Codex, Antigravity, Cursor, Windsurf, or any agent that can execute shell commands.

---

## Non-Goals for MVP

- UI / dashboard
- Cloud sync / multi-user
- MCP server wrapper (post-MVP — thin layer over CLI)
- Vector / semantic search
- Autonomous orchestration
- Markdown as source of truth

---

## Storage Architecture

### Location: One Global Store

```
~/.engram/
└── memory.db       ← single SQLite file, all projects live here
```

**Why global, not per-project `.lms/`:**

| Concern | Per-project `.lms/` | Global `~/.lms/` |
|:--------|:--------------------|:-----------------|
| Git pollution | Needs `.gitignore` entry | Zero repo impact |
| Repo moves/deletes | Memory lost | Memory survives |
| Multi-repo projects | Breaks — where does `.lms/` go? | Works — repo paths are just fields |
| Agent detection | Must walk dirs to find `.lms/` | Always at `~/.lms/` |
| Cross-project search | Impossible | Possible when needed |

Isolation is enforced via `project_id` on every row and a repo path binding registered at `engram init`. The system auto-detects your current project from `cwd` against the stored repo paths.

### Output Format

**Default: human-readable compact text** — optimized for agent context consumption.

Tool name: `engram`

```
T-003  Implement dedup logic  [in_progress]  priority:high  phase:1
```

**`--json` flag** available for scripting, piping to `jq`, or automated testing:

```bash
engram task next --json
```

No command documentation is pre-loaded into agent context. Agents use `engram --help` and `engram <cmd> --help` on-demand. The repo `AGENTS.md` contains only ~5 lines about `engram` (see Agent Bootstrap section).

---

### Schema

#### `projects`
```sql
CREATE TABLE projects (
    id          TEXT PRIMARY KEY,        -- e.g. "catalyst"
    name        TEXT NOT NULL,
    summary     TEXT,
    status      TEXT DEFAULT 'active',   -- active | paused | archived
    repo_paths  TEXT,                    -- JSON array of bound absolute paths
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);
```

#### `tasks`
```sql
CREATE TABLE tasks (
    id          TEXT PRIMARY KEY,        -- e.g. "T-001"
    project_id  TEXT NOT NULL REFERENCES projects(id),
    title       TEXT NOT NULL,
    description TEXT,
    status      TEXT DEFAULT 'backlog',  -- backlog|ready|in_progress|blocked|done|cancelled
    priority    TEXT DEFAULT 'medium',   -- low|medium|high|critical
    phase       TEXT,
    acceptance  TEXT,
    evidence    TEXT,
    tags        TEXT,                    -- JSON array
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);
```

#### `memories`
Unified table for decisions, lessons, constraints, and notes.

```sql
CREATE TABLE memories (
    id             TEXT PRIMARY KEY,     -- e.g. "M-001"
    project_id     TEXT NOT NULL REFERENCES projects(id),
    type           TEXT NOT NULL,        -- decision | lesson | constraint | note
    title          TEXT NOT NULL,
    content        TEXT NOT NULL,
    scope          TEXT DEFAULT 'project', -- global | project | task
    task_id        TEXT REFERENCES tasks(id),
    tags           TEXT,                 -- JSON array
    always_include BOOLEAN DEFAULT 0,   -- if true, included in every startup context
    created_at     TEXT DEFAULT (datetime('now')),
    updated_at     TEXT DEFAULT (datetime('now'))
);
```

#### `sessions`
```sql
CREATE TABLE sessions (
    id            TEXT PRIMARY KEY,      -- e.g. "S-001"
    project_id    TEXT NOT NULL REFERENCES projects(id),
    goal          TEXT,
    status        TEXT DEFAULT 'open',   -- open | closed
    summary       TEXT,                  -- filled on close (IS the checkpoint)
    changed_files TEXT,                  -- JSON array, filled on close
    checks_run    TEXT,                  -- JSON array, filled on close
    next_steps    TEXT,                  -- filled on close
    next_task_id  TEXT,                  -- filled on close
    started_at    TEXT DEFAULT (datetime('now')),
    closed_at     TEXT
);
```

#### `audit_log`
```sql
CREATE TABLE audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    target_table TEXT NOT NULL,
    target_id    TEXT NOT NULL,
    operation    TEXT NOT NULL,          -- create | update | delete
    field        TEXT,                   -- which field changed (updates only)
    old_value    TEXT,
    new_value    TEXT,
    timestamp    TEXT DEFAULT (datetime('now'))
);
```

#### FTS5 Index
```sql
CREATE VIRTUAL TABLE memories_fts USING fts5(
    title, content, tags,
    content='memories',
    content_rowid='rowid'
);
```

---

## CLI Interface

### Project Commands

```bash
engram init                               # Register current repo, create/bind to project
engram project get                        # Current project summary
engram project update --summary "..."     # Update project summary
engram project list                       # List all projects
```

### Task Commands

```bash
engram task create --title "..." --priority high --phase 1
engram task list                          # Non-done tasks (default)
engram task list --status done
engram task next                          # Next ready task
engram task get T-003                     # Full task detail
engram task start T-003                   # Set status=in_progress
engram task update T-003 --status blocked
engram task done T-003 --evidence "Tests pass, PR merged"
engram task note T-003 "Found edge case with empty arrays"
```

### Memory Commands

```bash
engram memory add --type decision --title "Use SQLite" --content "..." --tags "storage"
engram memory add --type lesson   --title "WAL mode needed" --content "..." --task T-003
engram memory add --type constraint --title "No cross-project writes" --always-include
engram memory get M-001
engram memory list
engram memory list --type decision
engram memory update M-001 --field content --value "Updated rationale..."
engram memory search "dedup strategy"
engram memory search "dedup" --type lesson --tags "data"
```

### Session Commands

```bash
engram session start --goal "Implement dedup logic"
engram session close \
    --summary "Implemented dedup with composite key" \
    --next-steps "Add edge case tests" \
    --changed-files "src/dedup.py,tests/test_dedup.py"
engram session latest                     # Last closed session (= last checkpoint)
```

### Context Commands

```bash
engram context startup                    # Compact startup context (< 500 tokens)
engram context task T-003                 # Task-specific context (< 800 tokens)
```

### Export Commands

```bash
engram export snapshot                    # → PROJECT_SNAPSHOT.md
engram export handoff                     # → SESSION_HANDOFF.md
```

---

## Agent Bootstrap (AGENTS.md entry)

This is **all** the agent needs to know about `engram` — ~5 lines, nothing more:

```markdown
## Memory System
This repo uses `engram` for persistent project memory.
Run `engram context startup` at the start of every session.
Run `engram session close --summary "..." --next-steps "..."` at the end of every session.
Use `engram --help` or `engram <command> --help` to discover all commands.
Memory is stored globally at ~/.engram/memory.db — do not edit directly.
```

The agent does **not** need a full command reference pre-loaded. `--help` is on-demand.

---

## Context Pack Specifications

### Startup Context — `lms context startup`

**Target: < 500 tokens. Human-readable text.**

```
Project: catalyst
Summary: Realtime lakehouse e-commerce platform

Current task: T-003 — Implement dedup logic [in_progress]

Last checkpoint (2026-05-11 18:00):
  Done: Implemented basic dedup with event_id matching
  Next: Handle edge case with empty arrays

Constraints:
  - No cross-project writes
  - Always run tests before marking task done

Pending tasks: 5
Tip: use 'engram task get T-003' for full detail, 'engram memory search <topic>' to find context
```

**What's included:**
- Project name + summary (2-3 lines)
- Current/next task title + status (title only, not full detail)
- Last session close summary + next_steps (2-3 lines)
- Memories with `always_include=true` (active constraints)
- Pending task count
- Hint for on-demand retrieval

**What's NOT included:**
- Full task descriptions or acceptance criteria
- All decisions/lessons (agent pulls via `lms memory search`)
- Full session history
- Command documentation

### Task Context — `lms context task T-003`

**Target: < 800 tokens.**

Includes full task detail, memories linked to this task, active constraints, and a search hint.

---

## Typical Session Workflow

### First-Time Setup (once per repo)

```bash
cd /path/to/catalyst
engram init --name "catalyst" --summary "Realtime lakehouse e-commerce platform"
# Registers repo path → project in ~/.engram/memory.db
```

### Every Agent Session

```text
1.  engram context startup             → compact context (~300 tokens)
2.  engram task get T-003              → full task when needed
3.  engram memory search "dedup"       → relevant memories on-demand
4.  ... agent works ...
5.  engram memory add --type lesson    → record what was learned
6.  engram task done T-003 --evidence  → mark complete
7.  engram session close --summary ... → checkpoint created
8.  engram export handoff              → optional, for human review
```

### Cross-Session Resumption

```text
New session → engram context startup
→ Returns last checkpoint + current task title
→ Agent knows exactly where to resume
→ Agent pulls details on-demand as needed
```

---

## Export Formats

### PROJECT_SNAPSHOT.md

Generated from SQLite. Replaces manually-maintained TASKS.md / DECISIONS.md / LESSONS.md.

```markdown
# Project: catalyst
Status: active | Updated: 2026-05-11

## Summary
Realtime lakehouse e-commerce platform...

## Tasks
| ID    | Title                            | Status      | Priority |
|-------|----------------------------------|-------------|----------|
| T-001 | Setup project                    | done        | high     |
| T-003 | Implement dedup logic            | in_progress | high     |

## Decisions
- M-001: Use SQLite for storage  [tags: storage, arch]
- M-003: Dedup uses event_id + subkey  [tags: dedup]

## Lessons
- M-002: WAL mode needed for concurrent reads  [tags: sqlite]

## Constraints
- No cross-project writes
- Always run tests before marking done
```

### SESSION_HANDOFF.md

```markdown
# Session Handoff — catalyst
Closed: 2026-05-11 18:00

## What Was Done
Implemented dedup with composite key (event_id + subcomponent)...

## Changed Files
- src/dedup.py
- tests/test_dedup.py

## Checks Run
- pytest: 12 passed, 0 failed

## Next Steps
- Handle edge case with empty arrays
- Add integration test for batch dedup

## Next Task
T-004: Add batch dedup integration tests
```

---

## Scope & Safety

| Level | Scope | Example |
|:------|:------|:--------|
| **global** | All projects | "Always use type hints in Python" |
| **project** | One project | "This project uses event_id dedup" |
| **task** | One task | "This task needs null handling" |

Safety rules:
- All writes scoped to current project (auto-detected from `cwd` → repo path binding)
- `lms init` registers the repo → project link
- No write touches another project without an explicit `--project` flag
- Audit log records every create/update/delete

---

## Build Order (6 Phases)

```
Phase 1 — Foundation
  ├── pyproject.toml + package scaffold
  ├── ~/.engram/ init + SQLite schema creation
  ├── engram init (repo path binding + project creation)
  └── engram project CRUD

Phase 2 — Core Entities
  ├── engram task CRUD + status lifecycle
  ├── engram memory CRUD + type/tag/scope/always_include
  └── Field-level updates (--field --value) + audit log

Phase 3 — Sessions & Context
  ├── engram session start / close (embedded checkpoint)
  ├── engram context startup (< 500 token target)
  └── engram context task

Phase 4 — Search
  ├── FTS5 virtual table + sync triggers on memories
  └── engram memory search (text + type + tag filters)

Phase 5 — Exports & Polish
  ├── engram export snapshot
  ├── engram export handoff
  └── Error handling, validation, edge cases

Phase 6 — Demo & Validation
  └── End-to-end demo scenario (acceptance test)
```

---

## Demo Scenario (Acceptance Test)

```bash
# Setup
engram init --name "catalyst" --summary "Realtime lakehouse e-commerce platform"

# Create task and memories
engram task create --title "Implement duplicate event simulation" --priority high --phase 1
engram memory add --type decision \
    --title "Dedup uses event_id plus subcomponent key" \
    --content "Composite key chosen for uniqueness across partial events" \
    --tags "dedup,arch"
engram memory add --type constraint \
    --title "No cross-project writes" \
    --always-include

# Session 1
engram session start --goal "Implement dedup logic"
engram context startup
# VERIFY: compact text output, < 500 tokens, shows T-001 + constraint

engram task start T-001
engram memory add --type lesson \
    --title "WAL mode needed for concurrent reads" \
    --content "Without WAL pragma, reads block during writes" \
    --task T-001 --tags "sqlite"
engram task done T-001 --evidence "All unit tests pass"
engram session close \
    --summary "Implemented dedup with composite key" \
    --next-steps "Add edge case tests for empty arrays" \
    --changed-files "src/dedup.py,tests/test_dedup.py"

# Session 2 — verify resumability
engram context startup
# VERIFY: shows last checkpoint summary and next steps

# Exports
engram export snapshot
engram export handoff
# VERIFY: readable markdown files generated from SQLite, not manually written
```

---

## Tech Stack

```
Language:      Python 3.10+
CLI:           click
Terminal UI:   rich  (used for --pretty / formatted tables)
Storage:       sqlite3  (Python stdlib — zero install)
Search:        SQLite FTS5  (built into SQLite)
Pip deps:      click, rich  (2 total)
Entry point:   engram  (via pyproject.toml [scripts])
Latency:       < 300ms per command (Python startup; DB ops < 10ms)
```

---

## Project File Structure

```
engram/
├── docs/
│   ├── mvp-project-plan.md           ← original plan (preserved)
│   └── refined-mvp-plan.md           ← this document (active plan)
├── src/
│   └── engram/
│       ├── __init__.py
│       ├── cli.py                    ← click entry point, command groups
│       ├── db.py                     ← schema, ~/.engram/ init, connection helper
│       ├── models/
│       │   ├── project.py
│       │   ├── task.py
│       │   ├── memory.py
│       │   └── session.py
│       ├── context.py                ← startup + task context generation
│       ├── search.py                 ← FTS5 search + filtering
│       ├── export.py                 ← snapshot + handoff markdown generation
│       └── audit.py                  ← audit log helpers
├── tests/
│   ├── test_project.py
│   ├── test_task.py
│   ├── test_memory.py
│   ├── test_session.py
│   ├── test_context.py
│   └── test_search.py
├── pyproject.toml
└── README.md
```

---

## Post-MVP Roadmap

- **MCP server wrapper** — thin layer over CLI; straightforward to add
- **Semantic / vector search** — upgrade FTS5, same interface
- **Cross-project search** — already possible via global DB, just needs a command
- **UI dashboard** — read-only view of `~/.lms/memory.db`
- **Automatic memory extraction** — agent auto-records decisions from conversation
- **Cloud sync** — export DB to remote store
