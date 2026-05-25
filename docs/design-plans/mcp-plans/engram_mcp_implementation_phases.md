# Engram MCP Implementation Phases

## Phase 0 — Lock decisions

Status: complete.

Final decisions:

```text
Tool naming:    engram_* prefix
MCP v1 scope:   read-only
Transport:      STDIO
Dependency:     optional extra, engram[mcp]
Entrypoint:     engram-mcp
Use case:       personal use + portfolio project
```

Implementation constraints:

```text
Do not shell out to CLI.
Do not access SQLite directly from MCP handlers.
Do not expose write tools in v1.
Do not expose workflow/commit/push tools in v1.
Do not import Click or Rich in services.
```

## Phase 1 — Add service foundation

Goal: create MCP-safe function boundaries without changing CLI behavior.

Files to add:

```text
src/engram/services/__init__.py
src/engram/services/errors.py
src/engram/services/serializers.py
src/engram/services/project_service.py
```

### 1.1 Add service errors

Implement:

```python
class EngramServiceError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }
```

Optional subclasses:

```python
class ProjectNotBoundError(EngramServiceError): ...
class NotFoundError(EngramServiceError): ...
class AmbiguousReferenceError(EngramServiceError): ...
class ValidationError(EngramServiceError): ...
```

Acceptance:

- errors carry `code`, `message`, and `details`
- no Click dependency
- no Rich dependency
- unit tests cover `to_dict`

### 1.2 Add serializers

Implement:

```python
def project_to_dict(project) -> dict
def task_to_dict(task) -> dict
def memory_to_dict(memory) -> dict
def phase_to_dict(phase) -> dict
```

Rules:

- return only JSON-safe values
- convert missing values to `None`
- keep list fields as lists
- keep booleans as booleans
- never return model objects
- include `effective_status` in task DTO if possible

Acceptance:

- serializer tests cover all DTO shapes
- task `tags` and `relevant_files` are lists
- memory `always_include` is boolean

### 1.3 Add project service

Implement:

```python
def resolve_current_project(cwd: str | None = None) -> dict
```

Behavior:

- use `os.getcwd()` if `cwd` is omitted
- call `Project.find_by_repo_path(cwd)`
- return ProjectDTO
- raise `PROJECT_NOT_BOUND` if no project is bound

Acceptance:

- works independently of CLI
- can be tested with temporary repo paths
- no Click/Rich import

## Phase 2 — Add read-only task service

Goal: support MCP task tools without importing `engram.cli`.

File to add:

```text
src/engram/services/task_service.py
```

Functions:

```python
def resolve_task_ref(project_id: str, task_ref: str) -> str

def list_tasks(
    project_id: str,
    status: str | None = None,
    phase: str | None = None,
) -> list[dict]

def get_task(project_id: str, task_ref: str) -> dict

def get_next_task(project_id: str) -> dict | None
```

Move or recreate service-safe versions of:

- exact/prefix task ID resolution
- ambiguous task reference detection
- valid status validation
- effective status calculation
- phase filter handling, if needed

Do not import from `engram.cli.task_helpers` if that imports Click.

Acceptance:

- exact task ID works
- unique task prefix works
- ambiguous task prefix raises `TASK_AMBIGUOUS`
- missing task raises `TASK_NOT_FOUND`
- invalid status raises `INVALID_TASK_STATUS`
- `status="all"` returns all tasks
- default status can remain `todo`
- no CLI dependency
- no direct raw DB access from MCP later; service may use models or internal DB helpers where justified

## Phase 3 — Add read-only memory service

File to add:

```text
src/engram/services/memory_service.py
```

Functions:

```python
def search_memories(
    project_id: str,
    query: str,
    type_filter: str | None = None,
    tags: list[str] | None = None,
    limit: int = 10,
) -> list[dict]

def list_memories(
    project_id: str,
    type_filter: str | None = None,
    limit: int | None = None,
) -> list[dict]
```

Behavior:

- call `Memory.search` for search
- call `Memory.list_by_project` or `Memory.list_by_type` for list
- apply `limit` in service
- validate limit is positive
- return MemoryDTO list

Acceptance:

- memory search returns JSON-safe DTOs
- empty search result returns empty list
- invalid limit raises `VALIDATION_ERROR`
- no Click/Rich import

## Phase 4 — Add phase service

File to add:

```text
src/engram/services/phase_service.py
```

Functions:

```python
def list_phases(project_id: str, status: str | None = None) -> list[dict]
def get_active_phase(project_id: str) -> dict | None
```

Behavior:

- use existing Phase model methods where available
- validate status filters
- return PhaseDTO list

Acceptance:

- phases serialize to JSON-safe DTOs
- `status="all"` returns all phases
- invalid status raises structured service error
- no CLI dependency

## Phase 5 — Add context service wrappers

File to add:

```text
src/engram/services/context_service.py
```

Functions:

```python
def get_startup_context_for_current_project(cwd: str | None = None) -> str

def get_snapshot_context_for_current_project(cwd: str | None = None) -> str

def get_handoff_context_for_current_project(cwd: str | None = None) -> str

def get_task_context_for_current_project(
    task_ref: str,
    cwd: str | None = None,
) -> str
```

Behavior:

- resolve current project through `project_service`
- call existing `engram.context` functions
- resolve task refs through `task_service` before task context

Acceptance:

- startup context works for current project
- task context works with exact and unambiguous task refs
- missing project/task returns structured service error
- no CLI dependency

## Phase 6 — Add MCP package and optional dependency

Files to add:

```text
src/engram/mcp/__init__.py
src/engram/mcp/server.py
src/engram/mcp/tools.py
src/engram/mcp/resources.py
src/engram/mcp/schemas.py
```

Update `pyproject.toml`:

```toml
[project.optional-dependencies]
mcp = [
    "mcp>=1.0,<2",
]
```

Update script entrypoints:

```toml
[project.scripts]
engram = "engram.cli:main"
engram-mcp = "engram.mcp.server:main"
```

Implementation notes:

- verify current MCP Python SDK API before final code
- server should initialize Engram DB once on startup
- use STDIO transport
- do not invoke Click CLI
- do not run subprocesses

Acceptance:

- `uv pip install -e ".[mcp]"` installs MCP dependencies
- `engram-mcp` command exists
- `engram-mcp` starts without requiring CLI invocation
- server startup fails clearly if MCP SDK is missing

## Phase 7 — Implement MCP resources

Add resources:

```text
engram://startup
engram://task/{task_id}/context
engram://snapshot
engram://handoff
```

Each resource should call `context_service`.

Acceptance:

- resources return strings
- resources work from a bound project working directory
- resources fail clearly when project is not initialized
- resources do not mutate DB
- resources do not shell out

Manual Codex test:

```text
Name: engram
Transport: STDIO
Command: engram-mcp
Working directory: target repo root
```

Ask Codex to retrieve startup context from Engram.

## Phase 8 — Implement MCP read-only tools

Add tools:

```text
engram_project_current
engram_task_list
engram_task_get
engram_task_next
engram_memory_search
engram_phase_list
```

### 8.1 `engram_project_current`

Service call:

```python
project_service.resolve_current_project()
```

Returns:

```json
{
  "ok": true,
  "project": {}
}
```

### 8.2 `engram_task_list`

Service calls:

```python
project_service.resolve_current_project()
task_service.list_tasks(project_id, status=status, phase=phase)
```

Returns:

```json
{
  "ok": true,
  "project": {},
  "tasks": []
}
```

### 8.3 `engram_task_get`

Service calls:

```python
project_service.resolve_current_project()
task_service.get_task(project_id, task_ref)
```

Returns:

```json
{
  "ok": true,
  "task": {}
}
```

### 8.4 `engram_task_next`

Service calls:

```python
project_service.resolve_current_project()
task_service.get_next_task(project_id)
```

Returns:

```json
{
  "ok": true,
  "task": {}
}
```

or:

```json
{
  "ok": true,
  "task": null
}
```

### 8.5 `engram_memory_search`

Service calls:

```python
project_service.resolve_current_project()
memory_service.search_memories(
    project_id,
    query=query,
    type_filter=type,
    tags=tags,
    limit=limit,
)
```

Returns:

```json
{
  "ok": true,
  "memories": []
}
```

### 8.6 `engram_phase_list`

Service calls:

```python
project_service.resolve_current_project()
phase_service.list_phases(project_id, status=status)
```

Returns:

```json
{
  "ok": true,
  "phases": []
}
```

Acceptance:

- all tools return JSON-safe dict/list values
- no Rich output
- no Click exceptions
- no raw DB rows
- no write operations
- errors preserve service error codes
- tests cover happy path and error path

## Phase 9 — Add tests

Add service tests:

```text
tests/test_services_project.py
tests/test_services_task.py
tests/test_services_memory.py
tests/test_services_phase.py
tests/test_services_context.py
```

Add MCP tests:

```text
tests/test_mcp_tools.py
tests/test_mcp_resources.py
```

Test priorities:

- current project resolution
- project-not-bound error
- task ID exact resolution
- task ID prefix resolution
- ambiguous task prefix error
- task list filtering
- next task behavior
- memory search limit/type/tag behavior
- phase listing
- context resource wrappers
- JSON serialization
- no Click/Rich imports in services
- MCP read-only tools do not mutate DB

Run:

```bash
uv run pytest tests/ -v
uv run ruff check src tests
```

Acceptance:

- service tests pass
- MCP tests pass when MCP extra is installed
- full existing test suite remains green

## Phase 10 — Add Codex setup docs

Add a Markdown doc:

```text
docs/mcp-codex-setup.md
```

Content:

```text
1. Install Engram with MCP extra:
   uv pip install -e ".[mcp]"

2. Initialize/bind a project if needed:
   engram init --name "..."

3. Open Codex custom MCP settings.

4. Use:
   Name: engram
   Transport: STDIO
   Command to launch: engram-mcp
   Arguments: none
   Working directory: target project repo root

5. Save and test:
   Ask Codex to call `engram_project_current`.
   Ask Codex to read `engram://startup`.
```

Acceptance:

- setup doc matches Codex screenshot fields
- includes troubleshooting for `PROJECT_NOT_BOUND`
- includes troubleshooting for missing `engram-mcp`

## Phase 11 — Refactor CLI gradually to use services

Do this after MCP v1 works.

Start with read-only CLI commands:

```text
engram task list
engram task get
engram memory search
engram context startup
engram context task
```

Refactor pattern:

```text
CLI command
  → service function
  → CLI renderer
```

Acceptance:

- CLI output remains compatible
- MCP behavior remains JSON
- existing CLI tests continue to pass
- duplicated validation starts shrinking

## Phase 12 — Add safe write tools later

Do not include in MCP v1.

Add service functions first:

```python
def create_task(...) -> dict
def update_task(project_id: str, task_ref: str, updates: dict) -> dict
def append_task_note(project_id: str, task_ref: str, note: str) -> dict
def create_memory(...) -> dict
```

Then add MCP tools:

```text
engram_task_create
engram_task_update
engram_task_note_append
engram_memory_create
```

Acceptance:

- all writes use model methods so audit logs remain intact
- unknown update fields are rejected
- invalid status/priority is rejected
- dependency cycles are rejected
- memory scope/level validation is preserved
- write tools return updated DTOs
- tests verify DB mutation is intentional

## Phase 13 — Add workflow tools only after write tools are stable

Potential tools:

```text
engram_phase_start
engram_phase_complete
engram_task_start
engram_task_done
```

Do not expose full `engram finish` automation until:

- dry-run behavior exists
- confirmation semantics are clear
- failure behavior is tested
- commit/push side effects are separately controlled

## Final checklist

- [ ] Add service error model
- [ ] Add serializers
- [ ] Add project service
- [ ] Add read-only task service
- [ ] Add read-only memory service
- [ ] Add phase service
- [ ] Add context service wrappers
- [ ] Add optional MCP dependency
- [ ] Add `engram-mcp` entrypoint
- [ ] Add STDIO MCP server
- [ ] Add read-only MCP resources
- [ ] Add read-only MCP tools
- [ ] Add service tests
- [ ] Add MCP tests
- [ ] Add Codex setup docs
- [ ] Refactor CLI gradually to use services
- [ ] Add safe write tools later
- [ ] Add workflow tools last
