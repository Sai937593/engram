# Implementation Plan - Task 28a30425

## Scope
Expose MCP phase lifecycle maintenance actions (`update`, `cancel`, `archive`) by delegating to existing phase lifecycle services, and close regression gaps for unsafe/invalid transitions without expanding beyond this task.

## Files
- src/engram/mcp/tools/phase_tools.py
- src/engram/mcp/tools/helpers.py
- src/engram/mcp/tools/__init__.py (only if export assertions require updates)
- tests/test_mcp_tools.py
- tests/test_mcp_server.py
- tests/test_services_phase.py (only if regression gap requires service-level assertion adjustments)

## Steps
1. Extend MCP phase tool registration with:
   - `engram_phase_update(phase_ref, title?, description?, acceptance?, evidence?)`
   - `engram_phase_cancel(phase_ref, reason?)`
   - `engram_phase_archive(phase_ref)`
2. Ensure each new tool:
   - resolves current project via `resolve_current_project`,
   - delegates lifecycle behavior to `update_phase`, `cancel_phase`, `archive_phase` service functions,
   - returns compact deterministic payloads via `_respond`,
   - maps service errors via `_respond_error` with actionable `fix` guidance.
3. Add/update MCP regression tests for:
   - tool registration presence,
   - successful update/cancel/archive responses,
   - invalid transition / unfinished-task blocking behavior surfaced through MCP errors,
   - phase-not-found and invalid input error surfacing.
4. Add/update helper fix mappings only if lifecycle errors currently lack actionable guidance for new MCP paths.
5. Run required verification target:
   - `uv run pytest tests/test_mcp_tools.py tests/test_mcp_server.py tests/test_services_phase.py -q`
6. If green, run full verification gate:
   - `uv run pytest -q` (if needed by workflow verify output)
   - `engram_workflow_verify`
7. Record memory review outcome on task `28a30425`, then run `engram_workflow_finish`.

## Constraints Checklist
- Exactly one Engram task this session: `28a30425`.
- No changes under `planning/`, `workflow/`, `.github/`.
- Keep service boundaries adapter-safe; MCP remains an adapter layer.
- Keep edits minimal and scoped to lifecycle MCP exposure + regression gaps.
