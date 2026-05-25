# Engram Memory Retrieval and Startup Context Implementation Plan

## Goal

Implement automatic memory retrieval in `engram start` after the Phase -> Task
hierarchy is stable.

This plan is intentionally FTS-first. SQLite FTS already exists in Engram, so
the first shippable version should use deterministic local keyword retrieval,
budgeted packing, and debug output before adding semantic retrieval.

## Dependency

This work starts after the first-class Phase -> Task hierarchy is stable:

```text
Project
  -> Phase
       -> Task
```

Memory scopes remain:

```text
project
task
```

No phase-memory scope in the initial design.

## Implementation Principles

```text
- one Engram task per implementation step
- tests first for schema/CLI/retrieval behavior
- no semantic dependency until local model/storage choices are explicit
- `engram start` must never fail because retrieval failed
- output budgets must be deterministic enough to test
```

## Phase 1 - Memory Schema and Migration Contract

### Objective

Make the memory model able to distinguish durable project memory from
retrievable task memory.

### Work Items

```text
- Add `level` column to memories if missing.
- Keep existing `scope` column and validate allowed values: project, task.
- Backfill existing memories using the design-spec migration defaults.
- Ensure project memories require level L0-L3.
- Ensure task memories have null/empty level.
- Keep task_id optional for task memories and treat it as origin/link metadata.
- Add model helpers for listing project guardrails and task-scope memories.
```

### Acceptance Criteria

```text
- Existing databases migrate without data loss.
- Existing constraints become scope=project, level=L1.
- Existing decisions become scope=project, level=L2.
- Existing task-linked memories become scope=task with no level unless explicitly project-scoped.
- Invalid scope/level combinations are rejected.
```

### Tests

```text
- migration adds level to old databases
- migration backfills type-based defaults
- Memory.create rejects scope=project without valid level
- Memory.create rejects scope=task with level
- Memory.from_row preserves level and scope
- project/task listing helpers only return matching scopes
```

## Phase 2 - Memory CLI Scope and Level UX

### Objective

Expose the storage contract through memory commands before retrieval depends on
it.

### Work Items

```text
- Add --scope, --level, and --task-id to `engram memory add`.
- Add scope, level, and task_id to valid `engram memory update` fields.
- Show scope, level, and task_id in memory list/detail output.
- Preserve typed shortcut commands.
- Update typed shortcut defaults:
  - constraint -> project/L1/always_include=true
  - decision -> project/L2/always_include=true initially
  - lesson -> task by default
  - snippet -> task by default
- Validate task_id belongs to the current project.
```

### Acceptance Criteria

```text
- Users can create project L0-L3 memories from CLI.
- Users can create task-scope reusable memories from CLI.
- Invalid combinations produce clear errors.
- Existing typed commands remain backwards-compatible enough for current workflows.
```

### Tests

```text
- memory add --scope project --level L1 succeeds
- memory add --scope project without --level fails
- memory add --scope task --level L1 fails
- memory add --scope task --task-id <id> succeeds for same-project task
- memory update supports scope/level/task_id with validation
- typed shortcut defaults are verified
```

## Phase 3 - Unified Startup Context Builder

### Objective

Create one context builder that `engram start` owns and that can be budgeted
section by section.

### Work Items

```text
- Add a startup context builder that accepts project, active phase, selected task, and options.
- Keep existing task context helpers for focused task context.
- Move `engram start` away from hard-constraints-only task context.
- Build sections:
  - project frame
  - current phase frame
  - current/next task frame
  - project guardrails from L0/L1 project memories
  - placeholder for retrieved task memories
  - next action
- Implement deterministic character-budget helpers.
```

### Acceptance Criteria

```text
- `engram start` output has stable sections.
- L0 and capped L1 project memories are shown separately from task memories.
- Output stays under the configured hard character budget.
- Empty/no-memory projects still render useful startup context.
```

### Tests

```text
- start context includes project, phase, task, guardrail, and next sections
- L1 guardrails are capped
- long project/phase/task text is compacted
- hard budget is enforced deterministically
- no-memory project does not crash
```

## Phase 4 - Task Retrieval Query Builder

### Objective

Build compact, deterministic query text from the selected task and phase.

### Work Items

```text
- Generate query text from task title, description, acceptance, tags.
- Include phase title, description, and acceptance.
- Omit or compact evidence logs.
- Add query object/metadata that debug output can show.
- Keep query builder independent from FTS and future semantic retrieval.
```

### Acceptance Criteria

```text
- Query text captures task intent and phase context.
- Query text ordering is deterministic.
- Query size is bounded.
- Debug mode can show exactly what was queried.
```

### Tests

```text
- query includes task title/description/acceptance/tags
- query includes phase title/description/acceptance
- query omits or compacts long evidence
- query output is stable across repeated calls
- missing optional fields do not create noisy blanks
```

## Phase 5 - FTS Task Memory Retrieval

### Objective

Retrieve useful task-scope memories using existing SQLite FTS before adding any
semantic dependency.

### Work Items

```text
- Add FTS search helper constrained to project_id and scope=task.
- Build an FTS-safe query from the retrieval query text.
- Retrieve top keyword candidates.
- Apply deterministic boosts:
  - exact title/tag hits
  - matching task_id/origin task
  - memory type priority if needed
- Return candidate metadata for debug output.
- Handle malformed/empty FTS queries gracefully.
```

### Acceptance Criteria

```text
- FTS retrieval works over task-scope memories only.
- Project guardrails are not mixed into task-memory retrieval.
- Malformed or empty queries do not break `engram start`.
- Results are deterministic enough to test.
```

### Tests

```text
- relevant task memory is retrieved by title/content/tag
- project-scope memory is excluded from task-memory retrieval
- current task_id match can be boosted
- malformed query falls back or returns no candidates without crashing
- retrieval returns rank/debug metadata
```

## Phase 6 - Memory Selection and Budgeted Packing

### Objective

Convert retrieved candidates into a compact memory pack for startup output.

### Work Items

```text
- Deduplicate candidates by memory ID.
- Sort by deterministic rank/boost order.
- Enforce section character budget.
- Enforce max K, default preferred K, and hidden count.
- Compact individual memory content when necessary.
- Return pack metadata for debug output.
```

### Acceptance Criteria

```text
- Duplicate memories are not shown.
- Final memory pack respects section budget and max K.
- Hidden/truncated counts are available.
- Output remains useful when candidate content is long.
```

### Tests

```text
- duplicate candidates are deduped
- max K is enforced
- section budget is enforced
- long memories are compacted
- hidden count is correct
- deterministic tie-breaking is stable
```

## Phase 7 - Integrate FTS Retrieval into `engram start`

### Objective

Make automatic task-memory retrieval part of normal startup output.

### Work Items

```text
- Insert the packed task-memory section into startup context.
- Keep project guardrails and task memories visually separate.
- Add retrieval timeout/failure fallback behavior.
- Add CLI option `engram start --debug-retrieval`.
- Ensure normal hook usage remains concise.
```

### Acceptance Criteria

```text
- `engram start` includes relevant task memories automatically.
- Retrieval failure does not prevent task start.
- Output remains under the hard budget.
- Debug flag is optional and off by default.
```

### Tests

```text
- `engram start` prints relevant task memory for selected task
- retrieval exception path still prints startup context
- hard output budget still holds with retrieved memories
- debug flag changes output only when requested
- no relevant memories yields a concise empty/omitted section
```

## Phase 8 - Memory Debug Command

### Objective

Allow retrieval quality to be inspected without mutating task state.

### Work Items

```text
- Add `engram memory related-to-task <task-id>`.
- Support `--debug` for query, candidates, ranks, boosts, selected items, hidden count, budget use.
- Reuse the same query builder, retriever, selector, and packer used by `engram start`.
```

### Acceptance Criteria

```text
- Users can inspect related memories for any task.
- Debug output explains why memories were selected or hidden.
- Command does not change task status or git branch.
```

### Tests

```text
- related-to-task shows selected memories
- --debug shows query/candidates/rank/budget metadata
- missing task gives a clear error
- command does not mutate task status
```

## Phase 9 - Evaluation and Tuning

### Objective

Tune FTS-first retrieval behavior using real examples before adding semantic
retrieval.

### Work Items

```text
- Collect examples where useful memories were missed.
- Collect examples where irrelevant memories were included.
- Adjust query construction, boosts, budgets, K, or thresholds.
- Document known retrieval failure modes.
- Decide whether semantic retrieval is justified yet.
- Evaluation artifact: `docs/design-plans/engram_memory_retrieval_phase9_evaluation_examples.md`.
```

### Acceptance Criteria

```text
- Several real tasks have been evaluated.
- Default K/budget values are validated or revised.
- Known FTS failure modes are documented.
- Semantic retrieval gets a go/no-go recommendation based on evidence.
```

### Tests

```text
- regression tests added for observed misses
- regression tests added for observed false positives
- budget regressions covered by startup tests
```

## Phase 11 - Local Semantic Retrieval

### Objective

Add semantic recall only after FTS-first retrieval is working and there is
evidence that exact matching misses important memories.

### Design Decisions (Recorded Before Implementation)

```text
Embedding library/model:
- Use `fastembed` with the default local model `BAAI/bge-small-en-v1.5`.
- Rationale: local-only inference, active release cadence, and lower runtime overhead
  than a full transformer stack for this CLI use case.

Vector storage format:
- Store semantic artifacts locally under `~/.engram/indexes/<project-id>/semantic/`.
- Keep two files:
  1) `embeddings.npy` (float32 matrix; row order is deterministic by memory id ASC)
  2) `metadata.json` (memory_id list, model name, dimension, schema version,
     indexed_at watermark, source_hash/version metadata)
- Keep source-of-truth memory text in SQLite; semantic files are a derived index.

Index freshness model:
- Metadata stores:
  - `model_name`, `model_dim`, `schema_version`
  - `indexed_memory_count`
  - `indexed_max_updated_at` (max of memory updated_at/created_at at build time)
  - `build_started_at`, `build_completed_at`, `build_status`
- Semantic index status enum:
  - `ready`: metadata present, model/schema match, watermark current
  - `missing`: no semantic artifacts found
  - `stale`: memory count/watermark mismatch vs current SQLite state
  - `incompatible`: model or schema mismatch
  - `error`: last build failed
- `engram start` must never rebuild automatically.

Reindex command UX:
- Add explicit CLI command:
  `engram memory reindex --semantic [--full] [--task-scope-only] [--model <name>] [--force]`
- Default behavior is incremental when metadata is compatible; `--full` rebuilds all.
- Command prints rows scanned, rows embedded, elapsed time, and resulting index status.

Dependency placement/pinning:
- Keep semantic dependencies optional in `pyproject.toml`:
  - `fastembed>=0.8,<1`
  - `numpy>=2.0,<3`
- Do not add to base `project.dependencies`; semantic retrieval is optional and local-first.

Fallback behavior:
- If status is `missing`, `stale`, `incompatible`, or `error`, startup retrieval uses FTS only.
- This fallback is silent in normal mode (no startup failure) and explicit in
  `--debug-retrieval` metadata (`semantic_status`, `semantic_reason`, `fallback_used=true`).

Deterministic fusion policy:
- Run FTS and semantic retrieval independently, then union by memory id.
- Preserve exact-match precision by always retaining top exact/boosted FTS hits before
  semantic-only additions.
- Apply deterministic ordering with tie-breakers:
  1) exact_fts_match desc
  2) combined_score desc
  3) channel_priority (fts before semantic when equal)
  4) memory_id asc
```

### Work Items

```text
- Add semantic index/storage abstraction.
- Add memory embedding/reindex command.
- Retrieve task memories by similarity to task query.
- Keep semantic retrieval independent from FTS retrieval.
- Fuse semantic and FTS candidates after both channels run independently.
- Show semantic index status in debug output.
```

### Acceptance Criteria

```text
- Semantic retrieval is local-first.
- Missing/stale index does not break `engram start`.
- FTS retrieval remains available as fallback.
- Fusion preserves exact-match candidates when useful.
```

## Out of Scope for Initial Retrieval Work

Do not include initially unless evidence demands it:

```text
- phase-memory scope
- remote embedding APIs as default
- required vector database server
- LLM-based relevance judge
- cross-encoder reranker
- complex per-dimension relevance scoring
- automatic full reindex inside start
- semantic retrieval before local model/storage choices are made
```

## Final Target

After the FTS-first phases, `engram start` should operate as:

```text
Resolve project
  -> Resolve active phase
  -> Resolve current/next task
  -> Build project frame + task frame
  -> Include L0/L1 project guardrails
  -> Build retrieval query from task + phase
  -> Retrieve task-scope memories with FTS
  -> Select and pack memories within budget
  -> Output prompt-ready startup context
```
