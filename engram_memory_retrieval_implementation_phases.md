# Engram Memory Retrieval and Startup Context Implementation Phase Plan

## Goal

Implement automatic memory retrieval in `engram start` after the Phase–Task hierarchy is stable.

This plan is architecture-level. It is intended to be split into concrete Codex tasks later.

## Dependency

This work should start after the Phase–Task hierarchy is implemented or mostly stable.

Expected structure:

```text
Project
  └── Phase
        └── Task
```

Memory scopes remain:

```text
project
task
```

No phase-memory scope in the initial design.

---

## Phase 1 — Memory Scope and Project Memory Levels

### Objective

Update memory classification to support project-level hierarchy and task-level retrieval.

### Work Items

```text
- Add memory scope field if not already present.
- Support `scope=project` and `scope=task`.
- Add level field for project memories.
- Validate that project memories have levels.
- Ensure task memories do not require levels.
```

### Expected Outcome

Engram can distinguish durable project context from retrievable task memories.

### Acceptance Criteria

```text
- Project memories can be assigned L0–L3.
- Task memories can remain flat.
- Existing memories can be migrated or defaulted safely.
- Memory commands can create/update scope and level.
```

---

## Phase 2 — Startup Context Builder

### Objective

Create a structured context builder for `engram start`.

### Work Items

```text
- Build project frame section.
- Build current phase frame section.
- Build current/next task frame section.
- Build project guardrail section from L0/L1 project memories.
- Add section budgeting.
- Add hard output budget.
```

### Expected Outcome

`engram start` output becomes structured and budget-aware before dynamic retrieval is added.

### Acceptance Criteria

```text
- Output includes project, phase, and task context.
- L0 project context is compressed.
- L1 project context is capped.
- Output does not grow unbounded.
```

---

## Phase 3 — Task Retrieval Query Builder

### Objective

Build high-quality retrieval text from current task and phase context.

### Work Items

```text
- Generate query text from task title, description, acceptance, phase, tags if available.
- Include current phase summary as context.
- Avoid including excessive evidence logs.
- Add debug visibility for generated query text.
```

### Expected Outcome

Retrieval has a reliable input representation.

### Acceptance Criteria

```text
- Query text is deterministic.
- Query text captures task intent.
- Query text remains compact.
- Debug mode can show the query.
```

---

## Phase 4 — Semantic Retrieval Layer

### Objective

Add semantic retrieval over task memories.

### Work Items

```text
- Add semantic index/storage abstraction.
- Add memory embedding/reindex command.
- Retrieve task memories by similarity to task query.
- Support stale/missing index fallback behavior.
- Avoid full reindexing inside `engram start`.
```

### Expected Outcome

Engram can retrieve conceptually relevant task memories automatically.

### Acceptance Criteria

```text
- Task memories can be indexed.
- `engram start` can retrieve semantic top candidates if index is ready.
- Missing/stale index does not break start.
- Retrieval remains local-first.
```

---

## Phase 5 — Keyword/FTS Retrieval Layer

### Objective

Add or adapt keyword retrieval as a parallel channel.

### Work Items

```text
- Ensure task memories are FTS-searchable.
- Build FTS query from same task query text.
- Retrieve top keyword candidates.
- Keep semantic and FTS retrieval independent.
```

### Expected Outcome

Exact technical matches can surface even when semantic retrieval misses them.

### Acceptance Criteria

```text
- FTS retrieval works over task memories.
- FTS retrieval does not gate semantic retrieval.
- FTS candidates are visible in debug mode.
```

---

## Phase 6 — Candidate Merge, Deduplication, and Fusion

### Objective

Combine semantic and FTS candidates into a final selected memory pack.

### Work Items

```text
- Deduplicate candidates by memory ID.
- Add simple fusion/reranking strategy.
- Select final memories within section budget.
- Enforce max K and hard token budget.
```

### Expected Outcome

`engram start` receives a compact, useful task-relevant memory pack.

### Acceptance Criteria

```text
- Duplicate memories are not shown.
- Final selection respects budget.
- Final selection includes both semantic and exact-match candidates when useful.
- Selection remains deterministic enough to debug.
```

---

## Phase 7 — Integrate Retrieval into `engram start`

### Objective

Make automatic memory retrieval part of normal startup output.

### Work Items

```text
- Insert task-relevant memory pack into `engram start`.
- Keep project guardrails separate from task memories.
- Add fallback behavior when retrieval fails or times out.
- Ensure one command works for both manual and hook usage.
```

### Expected Outcome

Agents receive relevant memory without needing to call memory search manually.

### Acceptance Criteria

```text
- `engram start` includes automatic task memory retrieval.
- Output includes project-level context and task-level memories separately.
- Retrieval failure does not break task start.
- Output remains within configured budget.
```

---

## Phase 8 — Debug and Observability

### Objective

Make retrieval behavior inspectable and tunable.

### Work Items

```text
- Add `engram start --debug-retrieval`.
- Add `engram memory related-to-task <task_id> --debug`.
- Show query, candidates, selected memories, ranks/scores, hidden count, latency.
- Show semantic index status.
```

### Expected Outcome

Retrieval quality can be evaluated and improved from real usage.

### Acceptance Criteria

```text
- Debug output explains why memories were selected.
- Hidden candidates can be inspected.
- Latency breakdown is visible.
- Index freshness is visible.
```

---

## Phase 9 — Evaluation and Tuning

### Objective

Tune retrieval behavior based on observed failures.

### Work Items

```text
- Collect examples where useful memories were missed.
- Collect examples where irrelevant memories were included.
- Adjust budgets, K, thresholds, or fusion.
- Decide whether additional ranking logic is needed.
```

### Expected Outcome

Retrieval quality improves without prematurely adding complexity.

### Acceptance Criteria

```text
- At least several real task examples are evaluated.
- Default K/budget values are validated.
- Known retrieval failure modes are documented.
- Future enhancements are prioritized from evidence.
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
```

## Final Target

After this plan, `engram start` should operate as:

```text
Resolve project
  ↓
Resolve active phase
  ↓
Resolve current/next task
  ↓
Include project frame + guardrails
  ↓
Retrieve task memories automatically
  ↓
Pack context within budget
  ↓
Output prompt-ready startup context
```
