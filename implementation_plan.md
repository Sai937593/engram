# Implementation Plan - Task fb4f6d14

## Scope
Switch executable queue semantics from `ready`/`todo` to `open` for task listing, workflow start, and maintenance/lifecycle transitions, and align MCP helper guidance accordingly. Keep finish/commit redesign out of scope.

## Files
- src/engram/services/workflow_service.py
- src/engram/services/task/crud.py
- src/engram/services/task/lifecycle.py
- src/engram/services/task/maintenance.py
- src/engram/mcp/tools/workflow_tools.py
- tests covering workflow start, task listing defaults, and maintenance/lifecycle transition behavior

## Steps
1. Confirm current queue selection defaults and start-selection logic paths in workflow and task service modules.
2. Update any remaining status normalization or default filters so executable queue behavior consistently targets `open`.
3. Align maintenance/unblock and lifecycle transition helpers so planned target states use `open` consistently (while keeping explicit compatibility behavior only where intentionally required).
4. Update MCP workflow helper text and blocked guidance to remove outdated instructions centered on promoting to `ready`/`todo`.
5. Add or adjust focused tests to prove:
   - default task listing includes/selects `open` as executable queue state,
   - workflow start chooses `open` tasks by default,
   - maintenance/lifecycle helpers target `open` consistently,
   - user-facing guidance no longer treats `ready`/`todo` as primary executable states.
6. Run focused tests first, then run `engram_workflow_verify`.
7. If verification passes, record memory review outcome (prefer `no_change` unless durable memory was produced), then run `engram_workflow_finish`.

## Constraints Checklist
- Stay within this task scope only.
- Do not edit `planning/`, `workflow/`, or `.github/`.
- Keep service-layer adapter boundaries intact.
- Do not edit files after verification passes unless verification is rerun.
