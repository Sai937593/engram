# Implementation Plan - Phase 13.1 (Task 94409614)

## Scope
Add service-layer foundations for memory lifecycle read/update so MCP adapters can fetch and mutate a single memory through project-safe DTO contracts.

## Files in scope
- src/engram/services/memory_service.py
- src/engram/services/serializers.py
- src/engram/models/memory/model.py
- tests/test_services_memory.py

## Plan
1. Add a project-scoped service read API to fetch one memory by id and return a JSON-safe DTO, with explicit not-found and cross-project access behavior.
2. Add a service update API that accepts an allowed writable field set, delegates mutation to the model helper path, and returns the updated project-scoped DTO.
3. Add validation helpers for update payload shape and writable fields (including scope/level/task_id consistency where applicable), reusing existing service error patterns.
4. Extend serializer coverage only if needed for writable fields to ensure stable DTO output for the new read/update contract.
5. Add targeted tests in `tests/test_services_memory.py` for:
   - successful get/update in-project,
   - not-found and foreign-project rejections,
   - invalid update field/value validation failures,
   - project scoping preserved after mutation.
6. Run `uv run pytest tests/test_services_memory.py -q` and fix any regressions within task scope.

## Non-goals
- No MCP handler refactor in this task.
- No schema migration outside fields required for service read/update contract.
- No work on additional Engram tasks in this session.
