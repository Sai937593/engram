# Implementation Plan - Task d8d0574d (Phase 7.4)

## Scope
Add regression coverage for Phase 7 verification behavior only: pass/fail execution outcomes, persisted verification state, and concise deterministic MCP-visible verification Markdown. Do not introduce Phase 8 stale-verification blocking, memory-review gates, or finish gating.

## Constraints and Boundaries
- One-task session only: execute only task `d8d0574d`.
- Phase boundary: stay strictly inside `engram_workflow_verify` + verification-state recording behavior.
- Output boundary: verification output must remain compact, deterministic, and fix-focused.
- Startup boundary: keep repo-local startup/MCP behavior protected from verification regressions.
- No-touch directories: `planning/`, `workflow/`, `.github/`.
- Service safety: no CLI/Click/Rich/subprocess/MCP adapter imports inside service-layer modules unless already part of existing verify service behavior.

## Investigation Plan
1. Inspect current verification coverage and identify gaps against acceptance:
- `tests/test_services_workflow_verify.py`
- `tests/test_workflow_redesign_phase_5_regressions.py`

2. Inspect MCP verification contract coverage and startup integration assertions:
- `tests/test_mcp_tools.py`
- `tests/test_mcp_server.py`

3. Inspect verification formatter/service contract needed for deterministic Markdown assertions:
- `src/engram/services/workflow_formatter.py`
- `src/engram/services/workflow_service.py`
- `src/engram/services/workflow_verification_service.py`

## Planned Changes
1. Service-layer regression tests (`tests/test_services_workflow_verify.py`):
- Ensure explicit coverage for both pass and fail runs.
- Assert persisted verification state captures status + summary/details shape for both outcomes.
- Keep assertions independent of Phase 8/9 behaviors.

2. MCP tool contract tests (`tests/test_mcp_tools.py`):
- Strengthen `engram_workflow_verify` response checks for deterministic concise Markdown:
  - status line present and stable (`PASSED`/`FAILED`)
  - single `## Next action` section
  - concise details summary (no long log dump assumptions)
- Preserve actionable error behavior when project has no repo binding/path.

3. MCP server/startup regression tests (`tests/test_mcp_server.py` and/or `tests/test_workflow_redesign_phase_5_regressions.py`):
- Add or tighten assertions that verification tool registration and startup-facing behavior do not regress while adding Phase 7.4 coverage.
- Keep tests repo-local and deterministic.

## Validation Plan
- Run targeted tests first:
- `pytest tests/test_services_workflow_verify.py`
- `pytest tests/test_mcp_tools.py -k workflow_verify`
- `pytest tests/test_mcp_server.py`
- `pytest tests/test_workflow_redesign_phase_5_regressions.py`

- Then run an aggregate verification-focused pass if needed:
- `pytest tests/test_services_workflow_verify.py tests/test_mcp_tools.py tests/test_mcp_server.py tests/test_workflow_redesign_phase_5_regressions.py`

## Out of Scope
- Blocking `engram_workflow_finish` based on verification state age/result.
- Any memory-review requirement changes.
- Broad workflow redesign changes outside verification tests.
- Refactoring production behavior unrelated to test coverage required by this task.
