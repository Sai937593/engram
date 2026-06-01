# Workflow Redesign Phase 0 Audit

## Scope

This note completes Phase 0 from `docs/CODEX_IMPLEMENTATION_PHASES_WORKFLOW_REDESIGN.md` for the workflow-redesign plan only. It is an audit and external-skill alignment pass, not a new redesign document.

## Active branch policy

- Active redesign/base branch for this session: `feat/workflow-mvp-simplification`
- Phase/task branches should branch from that active redesign/base branch.
- Any merge, rebase, or PR target should go back to that active redesign/base branch unless the user explicitly selects another target.
- Agents should not default to `main` for workflow-redesign phase handoff.

## Current storage and project-resolution surface

- Repo-local project state is already the normal path.
  - `src/engram/services/project_path.py`
  - `src/engram/services/project_service.py`
  - `src/engram/services/project_status_service.py`
- `initialize_project()` creates or reuses `project-root/.engram/memory.db`, writes project metadata, and ensures `.engram/` is present in `.gitignore`.
- `resolve_current_project()` resolves the repo-local DB first, then keeps a test-only fallback to legacy repo-path binding via `Project.find_by_repo_path(...)`.
- `get_current_project_status()` and `get_project_diagnostics()` already report `unresolved-workspace`, `uninitialized`, `healthy`, and `misconfigured` states with one next action.

## Current MCP and startup surface

- MCP stdio entrypoint remains Python-based and compact.
  - `src/engram/mcp/server.py`
  - `src/engram/mcp/__main__.py`
- Project init, current-project lookup, diagnostics, workflow start, workflow verify, and workflow finish are exposed through MCP tools in:
  - `src/engram/mcp/tools/workflow_tools.py`
- Startup task selection and branch checkout behavior live in:
  - `src/engram/services/workflow_service.py`
  - `src/engram/services/workflow_helpers.py`
- Startup next-action rendering lives in:
  - `src/engram/context/startup/next_action.py`

## Current workflow, task, memory, and phase surface

- Workflow execution is MCP-first for normal agent use; CLI workflow commands have already been removed from the main path.
- Task readiness, update, and lifecycle support already exist in:
  - `src/engram/services/task/crud.py`
  - `src/engram/services/task/lifecycle.py`
  - `src/engram/services/task/validation.py`
  - `src/engram/services/task/maintenance.py`
- Memory and phase lifecycle support already exist in:
  - `src/engram/services/memory_service.py`
  - `src/engram/services/memory_lifecycle_service.py`
  - `src/engram/services/phase_service.py`
  - `src/engram/services/phase_lifecycle_service.py`
- Workflow verification storage and gating already exist in:
  - `src/engram/services/workflow_verify_service.py`
  - `src/engram/services/workflow_verification_service.py`

## Gaps and mismatches found

1. External skill split needed explicit ownership
   - The old single phase-transition responsibility is now split across `engram-phase-review` and `engram-task-decomposition`.
   - Before this audit, only `engram-phase-review` carried the branch-target rule explicitly.

2. MCP finish guidance still references a nonexistent skill name
   - `src/engram/mcp/tools/workflow_tools.py`
   - Tests also assert that finish guidance points to `engram-phase-transition`:
     - `tests/test_workflow_redesign_phase_5_regressions.py`
     - `tests/test_workflow_redesign_phase_15_end_to_end.py`
   - This is an audit finding for later follow-up because the external skill was split rather than preserved under that name.

3. Legacy/test fallback still exists in project resolution
   - `resolve_current_project()` keeps a test-only fallback to older repo-path lookup.
   - This is acceptable for the current branch state but remains a Phase 0 note because later phases may want to reduce or isolate legacy behavior further.

4. Branch-aware behavior is implemented, but some tests still model `main`
   - Branch creation itself is phase-derived in `get_target_branch()` and does not hardcode `main`.
   - Several tests still initialize or mock the current branch as `main`, which is fine as fixture data but should not be confused with product policy.

## External skill update confirmation

- Updated `C:\Users\sai\.codex\skills\engram-phase-review\SKILL.md`
  - Explicitly states that it owns the branch-handoff portion of the older combined phase-transition workflow.
  - Explicitly states that agents should treat the active redesign/base branch as the default comparison point rather than assuming `main`.
- `C:\Users\sai\.codex\skills\engram-task-decomposition\SKILL.md` already avoided merge-target guidance and therefore did not need behavioral changes; its role remains decomposition only.

## File targets for later phases

- Repo-local DB and project resolution:
  - `src/engram/services/project_path.py`
  - `src/engram/services/project_service.py`
  - `src/engram/services/project_status_service.py`
  - `tests/test_db.py`
  - `tests/test_mcp_startup_reliability.py`
- MCP startup and packaging:
  - `src/engram/mcp/server.py`
  - `src/engram/mcp/__main__.py`
  - `tests/test_mcp_server.py`
  - `tests/test_mcp_main.py`
- Workflow output and finish/start guidance:
  - `src/engram/mcp/tools/workflow_tools.py`
  - `src/engram/mcp/tools/workflow_tool_helpers.py`
  - `src/engram/services/workflow_service.py`
  - `src/engram/services/workflow_formatter.py`
  - `tests/test_mcp_tools.py`
  - `tests/test_workflow_redesign_phase_5_regressions.py`
  - `tests/test_workflow_redesign_phase_15_end_to_end.py`
- Task, memory, phase, and startup-context surfaces:
  - `src/engram/services/task/`
  - `src/engram/services/memory_service.py`
  - `src/engram/services/memory_lifecycle_service.py`
  - `src/engram/services/phase_service.py`
  - `src/engram/services/phase_lifecycle_service.py`
  - `src/engram/context/startup/`
  - `tests/test_context.py`
  - `tests/test_services_workflow_start_basic.py`
  - `tests/test_services_workflow_finish.py`
  - `tests/test_services_workflow_verify.py`

## Verification run for Phase 0

- Planned focused checks:
  - `uv run pytest tests/test_db.py tests/test_mcp_startup_reliability.py tests/test_mcp_server.py tests/test_mcp_tools.py tests/test_context.py tests/test_services_workflow_start_basic.py tests/test_services_workflow_finish.py tests/test_services_workflow_verify.py tests/test_workflow_redesign_phase_5_regressions.py tests/test_workflow_redesign_phase_15_end_to_end.py -q`
- Skill grep:
  - confirm no remaining default-`main` merge-target guidance in the split external skills.
