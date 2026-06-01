# Implementation Plan - Phase 13.3 (Task b7119baf)

## Scope
Expose finalized memory lifecycle operations through MCP memory tools and refine `engram_memory_search` output to be compact, Markdown-first, and actionable while preserving safe failure guidance.

## Files in scope
- src/engram/mcp/tools/memory_tools.py
- src/engram/mcp/tools/helpers.py
- src/engram/services/memory_service.py (only if MCP adapter gaps require service-facing shape tweaks)
- tests/test_mcp_tools.py
- tests/test_mcp_server.py

## Plan
1. Audit existing MCP memory tool surface and map acceptance coverage for get, update, supersede, demote, archive, and delete to confirm missing/partial handlers.
2. Implement or refine thin MCP adapters so lifecycle tools delegate to memory services (no direct DB mutation/filter logic in MCP layer).
3. Update memory-search response formatting to Markdown-first compact output while preserving miss guidance and deterministic error/help text.
4. Ensure default discovery behavior still hides superseded/archived entries unless explicitly requested through maintenance/audit paths.
5. Add/adjust regression tests in MCP test suites for:
   - lifecycle happy paths,
   - compact actionable response contracts,
   - safe failure guidance for misses/invalid operations.
6. Run required verification commands:
   - `uv run pytest tests/test_mcp_tools.py tests/test_mcp_server.py -q`
   - `uv run pytest -q`

## Non-goals
- No schema redesign or model-layer rewrite beyond what is strictly needed for MCP delegation compatibility.
- No edits in `planning/`, `workflow/`, or `.github/`.
- No additional Engram task work in this session.
