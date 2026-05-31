# Implementation Plan - Task 7b19d707 (Phase 3.1)

## Scope
Refactor retained CLI startup and diagnostics so normal CLI bootstrap is side-effect free and no longer depends on legacy global repo-path binding assumptions.

## Current Findings
- `src/engram/cli/__init__.py` root Click callback calls `init_db()` unconditionally, causing DB initialization during generic CLI startup/help.
- `src/engram/cli/__init__.py` exposes `get_current_project()` that uses `Project.find_by_repo_path()`, representing legacy global binding behavior.
- `src/engram/cli/utils_cmds.py` `db` command reports `engram.db.DEFAULT_DB_PATH` and opens DB via global helper instead of resolving repo-local path via service-layer workspace resolution.

## Planned Changes
1. `src/engram/cli/__init__.py`
- Remove eager `init_db()` from root CLI callback.
- Remove legacy `get_current_project()` helper if unused by retained command surface.
- Keep command registration and entrypoint behavior stable (`init`, `guide`, `db`).

2. `src/engram/cli/utils_cmds.py`
- Refactor `db` command to resolve workspace through `engram.services.project_path` helpers.
- Report repo-local `.engram/memory.db` when executed inside a git repo.
- Degrade cleanly outside a repo (clear unresolved-workspace messaging; no crash).
- Perform explicit diagnostic DB touch/check only within command execution flow (not startup).

3. Tests
- Update/add CLI regression tests in `tests/test_cli_entrypoint.py` to cover:
  - Startup/help path does not initialize DB eagerly.
  - `engram db` inside repo reports/uses repo-local DB path.
  - `engram db` outside repo degrades cleanly.

## Validation Plan
- Run targeted tests:
  - `pytest tests/test_cli_entrypoint.py -q`
- If needed, run additional impacted suite:
  - `pytest tests/test_cli_entrypoint.py tests/test_init_cmds.py -q`

## Out of Scope
- Adding new CLI workflow commands.
- Changing MCP tool output contracts.
- Broad docs rewrite beyond task-relevant wording discovered during this refactor.
