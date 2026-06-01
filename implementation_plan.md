# Implementation Plan - Phase 13.2 (Task 5aff059a)

## Scope
Implement service-layer memory lifecycle mutations for safe supersede, demote, archive, and delete flows, preserving project scoping and deterministic validation/audit behavior.

## Files in scope
- src/engram/services/memory_service.py
- src/engram/models/memory/model.py
- src/engram/models/memory/helpers.py
- src/engram/models/memory/queries.py
- tests/test_services_memory.py
- tests/test_memory.py
- tests/test_memory_supersession.py

## Plan
1. Add explicit service-layer lifecycle APIs in `memory_service` for supersede, demote, archive, and delete that resolve memory by project scope and return JSON-safe DTOs where appropriate.
2. Implement deterministic validation contracts for each lifecycle action (missing memory, wrong scope/level for demote, invalid supersede target, and protected delete constraints), mapping model errors to service `ValidationError` payloads.
3. Keep reversible hygiene as first-class behavior: support supersede/archive/demote flows without changing default list/search behavior (superseded/archived excluded unless explicitly requested).
4. Extend model/helper paths only where needed to support archive and safe supersede semantics with audit logging and predictable state transitions.
5. Add/extend focused tests covering:
   - happy paths for supersede/demote/archive/delete,
   - deterministic failures and error codes,
   - default filter behavior unchanged,
   - regression preference for reversible actions over delete.
6. Run required verification tests:
   - `uv run pytest tests/test_services_memory.py tests/test_memory.py tests/test_memory_supersession.py -q`
   - `uv run pytest -q` only if targeted tests indicate broader regression risk.

## Non-goals
- No MCP adapter refactor beyond existing service delegation boundaries.
- No edits in `planning/`, `workflow/`, or `.github/`.
- No additional Engram task work in this session.
