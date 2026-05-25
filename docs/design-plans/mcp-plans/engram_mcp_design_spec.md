# Engram MCP Design Spec

## 1. Final decisions

This spec is optimized for personal use and portfolio value.

Locked decisions:

```text
Tool naming:    engram_* prefix
MCP v1 scope:   read-only
Transport:      STDIO first
Dependency:     optional extra, engram[mcp]
Entrypoint:     engram-mcp
Architecture:   MCP adapter over services, not CLI subprocess wrapper
```

## 2. Product goal

Engram should expose its local project memory, task state, phase state, and context-generation capabilities to MCP-capable coding agents such as Codex.

The MCP integration should make Engram usable as an agent-facing memory layer while preserving the CLI as the stable human and universal-agent interface.

## 3. Context: Codex custom MCP setup

The Codex custom MCP screen supports:

```text
Transport options:
- STDIO
- Streamable HTTP

STDIO fields:
- Name
- Command to launch
- Arguments
- Environment variables
- Environment variable passthrough
- Working directory

Streamable HTTP fields:
- Name
- URL
- Bearer token env var
- Headers
- Headers from environment variables
```

For Engram v1, use STDIO.

Recommended Codex configuration:

```text
Name:
  engram

Transport:
  STDIO

Command to launch:
  engram-mcp

Arguments:
  none

Environment variables:
  optional

Environment variable passthrough:
  optional

Working directory:
  target project repository root
```

Reason:

- Engram is local-first.
- Engram resolves the current project from the working directory.
- STDIO avoids hosting, ports, auth, and HTTP server lifecycle.
- STDIO fits personal local coding workflows.
- Streamable HTTP can be added later if remote/shared use becomes necessary.

## 4. Architecture

Target architecture:

```text
SQLite DB / Engram models
        ↑
Engram service layer
        ↑
 ┌──────┴──────┐
 CLI adapter   MCP adapter
```

Do not build:

```text
MCP tool → subprocess.run(["engram", ...])
```

Do not build:

```text
MCP tool → raw SQL directly
```

Correct flow:

```text
MCP tool/resource
  → service function
    → model method / context function
      → SQLite DB when needed
```

CLI flow:

```text
CLI command
  → service function
    → model method / context function
  → Rich/prose/table renderer
```

## 5. Rationale

### Why not a CLI subprocess wrapper?

A CLI wrapper is fast initially but weak architecturally:

- MCP needs structured JSON; CLI output is human/Rich/prose oriented.
- CLI wording changes could break MCP behavior.
- Subprocess calls are slower and harder to test.
- Error handling becomes stdout/stderr/exit-code based.
- Permissions and safe write controls become harder.
- It looks less credible as a portfolio architecture.

### Why not direct DB access from MCP?

MCP should not bypass existing model/domain behavior.

Direct DB access risks:

- duplicate validation
- skipped audit logs
- inconsistent task/memory behavior
- schema coupling
- brittle migrations
- duplicated business rules

MCP should call services. Services should reuse existing model methods.

## 6. Existing reusable internals

The current Engram code already has useful reusable internals.

Context functions:

```python
get_startup_context(project_id)
get_task_context(task_id)
get_snapshot_context(project_id)
get_handoff_context(project_id)
```

Model methods:

```python
Task.create(...)
Task.get(...)
Task.list_by_project(...)
Task.get_next(...)
Task.update(...)

Memory.create(...)
Memory.get(...)
Memory.search(...)
Memory.update(...)
```

These are good internal building blocks.

However, MCP should not call CLI command handlers or CLI helpers directly, because some CLI helpers currently depend on Click exceptions and terminal-oriented behavior.

## 7. Service layer

Add a thin service layer:

```text
src/engram/services/
  __init__.py
  errors.py
  serializers.py
  project_service.py
  task_service.py
  memory_service.py
  phase_service.py
  context_service.py
```

The service layer should:

- avoid Click
- avoid Rich
- avoid terminal formatting
- return JSON-safe DTOs
- centralize validation
- preserve model audit behavior
- translate domain failures into structured service errors
- be reusable from CLI and MCP

The service layer should not become a large parallel backend. It should remain thin.

## 8. Service error model

Create one base error:

```python
class EngramServiceError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        ...
```

Suggested error codes:

```text
PROJECT_NOT_BOUND
TASK_NOT_FOUND
TASK_AMBIGUOUS
TASK_DEPENDENCY_NOT_FOUND
TASK_DEPENDENCY_CYCLE
INVALID_TASK_STATUS
INVALID_TASK_PRIORITY
INVALID_TASK_FIELD
MEMORY_NOT_FOUND
INVALID_MEMORY_SCOPE
INVALID_MEMORY_LEVEL
PHASE_NOT_FOUND
VALIDATION_ERROR
```

MCP error envelope:

```json
{
  "ok": false,
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task 'abc' was not found in the current project.",
    "details": {
      "task_ref": "abc"
    }
  }
}
```

Success envelope:

```json
{
  "ok": true,
  "task": {
    "id": "abc123",
    "title": "Add MCP adapter",
    "status": "todo"
  }
}
```

## 9. DTOs

### ProjectDTO

```json
{
  "id": "project-id",
  "name": "engram",
  "summary": "Local-first project memory",
  "repo_path": "/path/to/repo"
}
```

### TaskDTO

```json
{
  "id": "task-id",
  "project_id": "project-id",
  "title": "Add MCP adapter",
  "description": null,
  "status": "todo",
  "effective_status": "todo",
  "priority": "high",
  "phase": null,
  "phase_id": null,
  "depends_on": null,
  "acceptance": null,
  "evidence": null,
  "tags": [],
  "relevant_files": []
}
```

### MemoryDTO

```json
{
  "id": "memory-id",
  "project_id": "project-id",
  "type": "decision",
  "title": "Use STDIO MCP first",
  "content": "STDIO fits local Codex workflows.",
  "scope": "project",
  "task_id": null,
  "tags": ["mcp"],
  "always_include": false,
  "level": "L2"
}
```

### PhaseDTO

```json
{
  "id": "phase-id",
  "project_id": "project-id",
  "title": "MCP v1",
  "description": null,
  "status": "active"
}
```

## 10. Package structure

Add:

```text
src/engram/mcp/
  __init__.py
  server.py
  tools.py
  resources.py
  schemas.py
```

Update `pyproject.toml`:

```toml
[project.optional-dependencies]
mcp = [
    "mcp>=1.0,<2",
]
```

Update scripts:

```toml
[project.scripts]
engram = "engram.cli:main"
engram-mcp = "engram.mcp.server:main"
```

The exact MCP SDK version should be verified during implementation. Keep MCP optional to preserve Engram's lightweight CLI install.

## 11. MCP resource design

Use resources for read-only context blobs.

### `engram://startup`

Purpose: return compact startup context for the current project.

Service:

```python
context_service.get_startup_context_for_current_project(cwd: str | None = None) -> str
```

### `engram://task/{task_id}/context`

Purpose: return focused task context.

Service:

```python
context_service.get_task_context_for_current_project(
    task_ref: str,
    cwd: str | None = None,
) -> str
```

### `engram://snapshot`

Purpose: return full project snapshot.

Service:

```python
context_service.get_snapshot_context_for_current_project(cwd: str | None = None) -> str
```

### `engram://handoff`

Purpose: return handoff context.

Service:

```python
context_service.get_handoff_context_for_current_project(cwd: str | None = None) -> str
```

## 12. MCP tool naming convention

Use:

```text
engram_<domain>_<action>
```

Reason:

- avoids collisions with other MCP servers
- makes Codex tool logs clearer
- improves portfolio readability
- keeps future GitHub/issue/task integrations unambiguous

## 13. MCP v1 tools: read-only

### `engram_project_current`

Purpose: verify current project binding and return project metadata.

Input:

```json
{}
```

Output:

```json
{
  "ok": true,
  "project": {}
}
```

### `engram_task_list`

Purpose: list tasks in current project.

Input:

```json
{
  "status": "todo | in-progress | done | blocked | cancelled | all | null",
  "phase": "phase id or title or null"
}
```

Output:

```json
{
  "ok": true,
  "project": {},
  "tasks": []
}
```

Default behavior should match CLI as much as practical: list `todo` tasks unless `status` is specified.

### `engram_task_get`

Purpose: get task details by exact ID or unambiguous prefix.

Input:

```json
{
  "task_ref": "abc123"
}
```

Output:

```json
{
  "ok": true,
  "task": {}
}
```

### `engram_task_next`

Purpose: return the next actionable task.

Input:

```json
{}
```

Output:

```json
{
  "ok": true,
  "task": {}
}
```

If there is no next task:

```json
{
  "ok": true,
  "task": null
}
```

### `engram_memory_search`

Purpose: search project memories.

Input:

```json
{
  "query": "sqlite migration",
  "type": "decision | lesson | constraint | snippet | note | null",
  "tags": [],
  "limit": 10
}
```

Output:

```json
{
  "ok": true,
  "memories": []
}
```

### `engram_phase_list`

Purpose: list project phases.

Input:

```json
{
  "status": "planned | active | done | cancelled | all | null"
}
```

Output:

```json
{
  "ok": true,
  "phases": []
}
```

## 14. MCP v2 tools: safe writes

Add only after read-only MCP is stable.

### `engram_task_create`

Input:

```json
{
  "title": "Add MCP adapter",
  "description": null,
  "priority": "medium",
  "phase_id": null,
  "depends_on": null,
  "acceptance": null,
  "tags": [],
  "relevant_files": []
}
```

### `engram_task_update`

Input:

```json
{
  "task_ref": "abc123",
  "updates": {
    "status": "in-progress",
    "priority": "high"
  }
}
```

### `engram_task_note_append`

Input:

```json
{
  "task_ref": "abc123",
  "note": "Implemented service serializer."
}
```

### `engram_memory_create`

Input:

```json
{
  "type": "decision",
  "title": "Use MCP STDIO",
  "content": "STDIO is the v1 transport.",
  "scope": "project",
  "task_ref": null,
  "tags": ["mcp"],
  "always_include": false,
  "level": "L2"
}
```

## 15. MCP v3 tools: workflow writes

Potential later tools:

```text
engram_phase_start
engram_phase_complete
engram_task_start
engram_task_done
```

Do not expose full `engram finish` behavior early.

Reason:

- it may validate, commit, push, and mutate task state
- MCP tools can be called autonomously by agents
- destructive/external side effects require stricter confirmation semantics

## 16. Security and safety

MCP v1 should:

- operate only on the current project resolved from working directory
- never expose arbitrary SQL
- never read unrelated local files
- never write repository files
- never shell out
- never mutate DB in read-only tools
- validate enum inputs
- return structured errors
- use model/service methods so audit behavior is preserved later

## 17. Personal-use and portfolio framing

This implementation should show:

```text
Engram started as a local CLI memory/task system.
A thin service layer decoupled core logic from CLI rendering.
The same core was exposed through MCP as typed tools/resources for AI coding agents.
```

This is a stronger portfolio story than a subprocess wrapper because it demonstrates:

- adapter architecture
- interface separation
- local-first design
- agent tool design
- structured JSON contracts
- staged safety for write tools

## 18. Acceptance criteria

MCP v1 is complete when:

- `engram-mcp` starts over STDIO
- Codex can register it through the custom MCP STDIO screen
- `engram://startup` works from a bound project working directory
- `engram_task_list` returns JSON-safe tasks
- `engram_task_get` resolves exact and unambiguous task IDs
- `engram_memory_search` returns JSON-safe memories
- `engram_phase_list` returns JSON-safe phases
- MCP v1 uses services, not CLI subprocess calls
- MCP handlers do not access SQLite directly
- read-only MCP tools do not mutate DB
- tests pass with `uv run pytest tests/ -v`
