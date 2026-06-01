# Implementation Plan - Phase 6.1 Finish Memory-Review Gate Removal

## Scope
Remove finish-time dependency on `memory_review_outcome` from workflow finish flow, while preserving compatibility for existing task fields and update APIs.

## Planned Changes
1. Update `src/engram/services/workflow_service.py`:
- Remove `MEMORY_REVIEW_OUTCOME_MISSING` block from `finish_workflow`.
- Remove finish-time validation call for `memory_review_outcome`.
- Keep existing verification and git eligibility gates unchanged.
- Keep returning `memory_review_outcome` in success payload for backward compatibility.

2. Update `src/engram/mcp/tools/workflow_tool_helpers.py`:
- Remove `MEMORY_REVIEW_OUTCOME_MISSING` from finish gate error code set.
- Remove special blocked guidance branch that instructs setting `memory_review_outcome`.
- Keep verify/staging guidance behavior intact.

3. Verify MCP wrapper behavior in `src/engram/mcp/tools/workflow_tools.py`:
- Ensure finish blocked formatting still routes only for remaining finish gate codes.
- No output expansion; keep response compact.

4. Confirm formatter behavior in `src/engram/services/workflow_formatter.py`:
- No required structural changes.
- Keep optional display of `memory_review_outcome` when present.

## Validation
- Run focused tests for workflow service and MCP workflow tool paths.
- Run any targeted project checks necessary to confirm no regressions in finish behavior.

## Out of Scope
- Removing `memory_review_outcome` from task models, persistence schema, or task update APIs.
- Broader workflow redesign beyond finish-time gating.