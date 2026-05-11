# Engram MVP — Implementation Tasks

> Derived from: `refined-mvp-plan.md`
> Rule: **one sub-task = one agent session / one chat**
> Each task has a clear entry point, bounded scope, and a testable done condition.

---

## How to Use This

### Phase 1 (P1.1 → P1.3) — engram doesn't exist yet
- Use this file as a plain checklist only
- Tick `[x]` after each sub-task manually
- Track notes in the session however you like (plain text, chat, etc.)

### Phase 2 onwards — dogfood engram on itself
Once P1.3 is done (`engram init` works), run:
```bash
cd path/to/engram-repo
engram init --name "engram" --summary "Local CLI memory system for AI agents"
```
Then for every subsequent sub-task:
1. `engram session start --goal "<task title>"`
2. Do the work
3. Verify the done condition
4. `engram session close --summary "..." --next-steps "..."`
5. Mark `[x]` here

This is intentional — using engram to build engram will surface real bugs earlier than the Phase 6 demo.

---

## Phase 1 — Foundation

- [ ] **P1.1 — Package scaffold**
  - Create `pyproject.toml` with `click`, `rich` deps and `engram` entry point
  - Create `src/engram/__init__.py`, `src/engram/cli.py` (top-level click group, no commands yet)
  - Verify: `pip install -e .` succeeds; `engram --help` prints usage

- [ ] **P1.2 — Database init (`db.py`)**
  - Create `src/engram/db.py`
  - Implement `~/.engram/` dir creation, SQLite connection helper, WAL mode pragma
  - Create all 5 tables: `projects`, `tasks`, `memories`, `sessions`, `audit_log`
  - Create FTS5 virtual table `memories_fts`
  - Verify: running `python -c "from engram.db import get_conn; get_conn()"` creates `~/.engram/memory.db` with correct schema (`sqlite3 ~/.engram/memory.db .tables`)

- [ ] **P1.3 — `engram init` + project CRUD**
  - Create `src/engram/models/project.py` — create, get, list, update project
  - Wire `engram init`, `engram project get`, `engram project list`, `engram project update` into `cli.py`
  - Implement auto-detection of current project from `cwd` → `repo_paths` binding
  - Verify: `engram init --name test --summary "test project"` → `engram project get` returns correct output

---

## Phase 2 — Core Entities

- [ ] **P2.1 — Task CRUD**
  - Create `src/engram/models/task.py` — create, get, list, update, status lifecycle
  - Wire `engram task create`, `task list`, `task get`, `task start`, `task update`, `task done`, `task note`
  - Verify: create a task → list shows it → `task start T-001` → status = `in_progress` → `task done T-001 --evidence "..."` → status = `done`

- [ ] **P2.2 — Memory CRUD**
  - Create `src/engram/models/memory.py` — create, get, list, update with type/tag/scope/always_include
  - Wire `engram memory add`, `memory get`, `memory list`, `memory update`
  - Verify: add a `decision` memory with `--always-include` → `memory list --type decision` shows it → `memory update M-001 --field content --value "new"` updates correctly

- [ ] **P2.3 — Field-level updates + audit log**
  - Create `src/engram/audit.py` — `log_change(table, id, operation, field, old, new)`
  - Hook audit writes into every create/update/delete in `project.py`, `task.py`, `memory.py`
  - Verify: after `task done T-001`, `SELECT * FROM audit_log` shows the status field change with old/new values

---

## Phase 3 — Sessions & Context

- [ ] **P3.1 — Session start/close**
  - Create `src/engram/models/session.py`
  - Wire `engram session start --goal "..."` and `engram session close --summary ... --next-steps ... --changed-files ...`
  - `session close` fills `summary`, `changed_files`, `checks_run`, `next_steps`, `closed_at` in one operation
  - Wire `engram session latest` — returns last closed session
  - Verify: `session start` → `session close` → `session latest` returns the checkpoint with all fields

- [ ] **P3.2 — `engram context startup`**
  - Create `src/engram/context.py`
  - Implement startup context assembly: project name+summary, current task title+status, last session summary+next_steps, `always_include` memories, pending task count, retrieval hint
  - Target: output must be **< 500 tokens**
  - Verify: output is human-readable compact text; token count it manually or with `tiktoken`; all required fields present

- [ ] **P3.3 — `engram context task`**
  - Extend `context.py` with task context: full task detail, linked memories, active constraints, search hint
  - Wire `engram context task T-001`
  - Target: **< 800 tokens**
  - Verify: `engram context task T-001` shows description, acceptance, evidence, linked memories

---

## Phase 4 — Search

- [ ] **P4.1 — FTS5 sync triggers**
  - In `db.py` (or a migration step): add `AFTER INSERT`, `AFTER UPDATE`, `AFTER DELETE` triggers on `memories` to keep `memories_fts` in sync
  - Verify: insert a memory → `SELECT * FROM memories_fts WHERE memories_fts MATCH 'yourterm'` returns it

- [ ] **P4.2 — `engram memory search`**
  - Create `src/engram/search.py`
  - Implement FTS5 text search + optional `--type` filter + optional `--tags` filter
  - Wire `engram memory search "query"` and `engram memory search "query" --type lesson --tags "sqlite"`
  - Verify: search returns ranked results; type/tag filters narrow correctly; no results for unmatched query

---

## Phase 5 — Exports & Polish

- [ ] **P5.1 — `engram export snapshot`**
  - Create `src/engram/export.py`
  - Generate `PROJECT_SNAPSHOT.md` from SQLite: project summary, tasks table, decisions, lessons, constraints
  - Wire `engram export snapshot`
  - Verify: output matches the format in `refined-mvp-plan.md`; generated from DB, not hardcoded

- [ ] **P5.2 — `engram export handoff`**
  - Extend `export.py` with `SESSION_HANDOFF.md`: what was done, changed files, checks run, next steps, next task
  - Wire `engram export handoff`
  - Verify: output matches the format in `refined-mvp-plan.md`

- [ ] **P5.3 — Error handling + validation**
  - Add input validation across all commands: unknown IDs, missing required flags, invalid status transitions, empty DB edge cases
  - Add `--json` flag to key commands (`task next`, `task get`, `memory list`, `context startup`)
  - Verify: `engram task get INVALID` gives clear error; `engram task next --json` returns valid JSON

---

## Phase 6 — Demo & Validation

- [ ] **P6.1 — Test suite**
  - Write `tests/test_project.py`, `test_task.py`, `test_memory.py`, `test_session.py`, `test_context.py`, `test_search.py`
  - Use a temp DB (fixture) so tests don't touch `~/.engram/memory.db`
  - Verify: `pytest` passes with no failures

- [ ] **P6.2 — End-to-end demo**
  - Run the full demo scenario from `refined-mvp-plan.md` (the acceptance test block, line-by-line)
  - Verify each checkpoint marked `# VERIFY:` in the plan
  - Fix any failures found
  - Verify: all VERIFY checks pass; `engram context startup` after session 2 shows checkpoint from session 1

---

## Summary

| Phase | Sub-tasks | Estimated sessions |
|:------|:----------|:-------------------|
| Phase 1 — Foundation | P1.1, P1.2, P1.3 | 3 |
| Phase 2 — Core Entities | P2.1, P2.2, P2.3 | 3 |
| Phase 3 — Sessions & Context | P3.1, P3.2, P3.3 | 3 |
| Phase 4 — Search | P4.1, P4.2 | 2 |
| Phase 5 — Exports & Polish | P5.1, P5.2, P5.3 | 3 |
| Phase 6 — Demo & Validation | P6.1, P6.2 | 2 |
| **Total** | **16 sub-tasks** | **~16 sessions** |

---

## Notes

- **P1.2 must precede everything** — all other tasks depend on `db.py` and the schema
- **P2.3 (audit log) can be done alongside P2.1/P2.2** if preferred — low risk
- **P3.2 (`context startup`) is the only task with a soft design decision** — use a smarter model (GPT-5.4/GPT-5.5 or Gemini 3 Pro) if output quality is poor on first attempt
- **P4.1 (FTS5 triggers) can be added back into P1.2** if you want — it's SQL only, no Python
- Order within a phase is flexible; order across phases is strict (1 → 2 → 3 → 4 → 5 → 6)
