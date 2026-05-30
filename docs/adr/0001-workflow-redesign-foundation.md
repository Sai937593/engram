# ADR 0001: Workflow Redesign Foundation

## Status

Accepted

## Context

Engram is being redesigned for a Codex/MCP-first workflow. The goal is to reduce ambiguity for coding agents, avoid duplicated or noisy tool outputs, enforce task quality gates, respect active redesign branches, and keep project memory fresh across sessions.

This ADR records the foundational decisions that Codex should treat as fixed unless the user explicitly approves a change.

---

## Decisions

| Area | Decision |
|---|---|
| Project storage | Use repo-local `.engram/memory.db` as the only normal project state store. |
| Global DB | Do not keep global DB as primary project storage. |
| Project resolution | Resolve the active project from the current repo/workspace and local `.engram`, not from global repo-path binding. |
| MCP setup | Configure MCP once per client/machine; do not require per-project MCP command changes. |
| New project init | Initialize project state through MCP by creating `.engram/memory.db`, project metadata, and `.gitignore` entry for `.engram/`. |
| Product surface | Make Engram MCP-first; normal Codex workflows must not depend on CLI commands. |
| CLI role | Do not introduce new workflow functionality only in CLI. CLI may remain only for temporary diagnostics/migration if needed. |
| Packaging | Keep Python + uv packaging/runtime. Do not rewrite Engram in Node/npm for this redesign. |
| Branch policy | Do not assume `main` is always the integration branch. Skills and workflow guidance must respect the current/base branch for the active redesign session. |
| Primary execution loop | Keep `workflow_start -> workflow_verify -> memory review -> workflow_finish`. |
| Workflow outputs | Make primary workflow outputs Markdown-first, compact, non-duplicative, and state-aware. |
| Finish behavior | Do not auto-start or instruct the agent to claim the next task from `workflow_finish`. |
| Verification | `workflow_finish` must be blocked unless verification passed and is not stale. |
| Memory hygiene | Force memory review before finish; do not force memory creation for every task. |
| Memory review detail | Put detailed memory-review reasoning in a skill, not in large tool outputs. |
| Task quality | Use draft/ready task lifecycle so incomplete tasks cannot be started. |
| Task decomposition | Use a task decomposition skill for turning implementation phase docs into complete Engram tasks. |
| Guardrails | Keep guardrails/L0/L1 memories as the durable project context model. Do not add Project Card as a new abstraction now. |
| CRUD/lifecycle tools | Provide safe domain-level lifecycle tools, but keep them as maintenance/admin tools, not the main workflow path. |
| Raw DB access | Do not expose raw database writes to agents. Use service/MCP domain tools. |

---

## Consequences

- Engram project state becomes portable at the repo level without relying on global project bindings.
- MCP server startup must discover the repo/workspace and local `.engram` state deterministically.
- Existing global DB behavior and `repo_paths`-based project resolution should be removed, deprecated, or limited to migration only.
- Any useful CLI behavior must move into service-layer functions and MCP tools/resources.
- Skills and workflow guidance must avoid hardcoded `main` assumptions during long-running redesign work.
- Codex should operate through workflow gates rather than passive hints.
- Memory freshness is enforced through a review gate without creating low-value memories on every task.
- Implementation can vary, but these decisions should not be reversed without user approval.

---

## Related Documents

- `docs/CODEX_HANDOFF_WORKFLOW_REDESIGN.md`
- `docs/CODEX_IMPLEMENTATION_PHASES_WORKFLOW_REDESIGN.md`
