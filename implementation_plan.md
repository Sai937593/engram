# Implementation Plan - Phase 14.1 (Task ae8430b3)

## Scope
Extend task lifecycle services so maintenance flows can block, unblock, cancel, and archive/delete tasks through service-layer transitions with deterministic validation and JSON-safe payloads.

## Files in scope
- src/engram/services/task/lifecycle.py
- src/engram/services/task/crud.py
- src/engram/services/task/validation.py
- src/engram/models/task/model.py (only if status enums/metadata fields are required)
- tests/test_services_task.py

## Plan
1. Audit current task service APIs and existing status transition guards for start/done/update to identify reusable validation hooks.
2. Add explicit service operations for:
   - block task
   - unblock task
   - cancel task
   - archive/delete-style retirement (matching existing model semantics)
3. Implement deterministic validation errors for illegal transitions (invalid source status, active-task invariants, dependency/task-safety constraints).
4. Ensure each new operation returns stable JSON-safe task payloads consistent with current service response shape.
5. Add focused regression tests in `tests/test_services_task.py` for:
   - happy paths for each lifecycle transition
   - invalid transition failures with clear error codes/messages
   - one-task-at-a-time workflow invariants preserved
6. Run required verification command:
   - `uv run pytest tests/test_services_task.py -q`

## Non-goals
- No direct model mutations from MCP adapters.
- No changes in `planning/`, `workflow/`, or `.github/`.
- No additional Engram task work in this session.
