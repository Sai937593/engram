# Engram Memory Retrieval and Startup Context Design Spec

## 1. Purpose

This design defines how Engram should automatically surface relevant memory in `engram start`.

The goal is to prevent agents from skipping memory search while keeping startup context useful, compact, local-first, and low-friction.

This design assumes the Phase–Task hierarchy exists or is being implemented separately:

```text
Project
  └── Phase
        └── Task
```

## 2. Core Design Decision

Use two memory scopes:

```text
project
task
```

Do not introduce phase-memory scope initially.

Use phase as planning context, not as a memory plane.

## 3. Memory Planes

### Project Memory Plane

Purpose:

```text
Keep the agent aligned with durable project/product constraints.
```

Project memories are hierarchical.

Recommended levels:

```text
L0 = project identity / core principles
L1 = non-negotiable constraints
L2 = architecture decisions
L3 = situational project knowledge
```

Examples:

```text
L0: Engram is a local-first, agent-agnostic memory CLI.
L1: Normal workflows should avoid remote dependencies.
L1: Startup context must avoid prompt stuffing.
L2: SQLite is the core storage layer.
L3: Semantic retrieval can be used when pre-indexed and latency-bounded.
```

### Task Memory Plane

Purpose:

```text
Surface reusable work-derived knowledge relevant to the current task.
```

Task memories are flat chunks.

They do not need levels initially.

Examples:

```text
- Previous bug fix lesson
- Useful debugging note
- Prior implementation decision
- Snippet or workflow note
- Trap discovered while working on a similar task
```

## 4. Startup Context Philosophy

`engram start` should become the primary context router.

It should not rely on the agent to remember:

```bash
engram memory search ...
```

Instead, `engram start` should automatically include a relevant memory pack.

Recommended startup structure:

```text
1. Project frame
2. Current phase frame
3. Current/next task frame
4. Project-level guardrails
5. Task-relevant memory pack
6. Next action
```

## 5. Output Budget

The earlier 800–1,000 token target is likely too restrictive for hook-based Codex usage.

Recommended default:

```text
target: 1,500–2,000 tokens
hard max: 3,000 tokens
```

Suggested allocation:

```text
Project frame:              150–250 tokens
Current phase:              150–300 tokens
Current task:               250–400 tokens
Project-level memories:     300–500 tokens
Task-relevant memories:     700–1,200 tokens
Next action:                100–200 tokens
```

The goal is not to use the full model context window. The goal is to provide a dense, high-signal startup pack.

## 6. Project Memory Inclusion Policy

Project memories should not all be dumped every time.

Recommended policy:

```text
L0: always included, compressed
L1: included by default, capped
L2: included only if relevant or if space allows
L3: usually retrieved/omitted unless relevant
```

Initial simpler policy:

```text
Include L0 compressed.
Include up to 3–6 L1 memories.
Skip L2/L3 unless later retrieval supports them.
```

## 7. Task Memory Retrieval

Task memories should be retrieved dynamically from the active/next task.

Query source:

```text
task.title
task.description
task.acceptance
task.phase/current phase summary
task.tags, if available
recent evidence summary, optional
```

Retrieval should use two channels:

```text
semantic retrieval
keyword/FTS retrieval
```

These should run in parallel, not as sequential filters.

Correct:

```text
Semantic retrieval ┐
                   ├─ dedupe → rerank/fuse → select → pack
FTS retrieval      ┘
```

Incorrect:

```text
FTS retrieval → semantic rerank only FTS results
```

## 8. Ranking and Fusion

High-level requirement:

```text
Task memory retrieval should combine semantic recall with exact keyword precision.
```

The exact model/tool choices can be decided during implementation.

Architectural options:

```text
v1: semantic-first with FTS fallback/exact hits
v2: semantic + FTS with rank fusion
v3: optional reranker only if observed quality requires it
```

The recommended long-term design is hybrid retrieval with simple fusion, not a full RAG stack.

## 9. Top-K and Selection Policy

Do not use a fixed K as the only control.

Use:

```text
token budget
relevance threshold
deduplication
maximum K
```

Recommended task memory selection:

```text
preferred: 5–8 memories
hard max: 10 memories
section budget: 700–1,200 tokens
```

Project memory selection:

```text
L0: always compressed
L1: 3–6 items
L2/L3: conditional
```

## 10. Latency Policy

Because `engram start` may be run through a session-start hook, some latency is acceptable.

Recommended budget:

```text
ideal: under 1.5 seconds
acceptable: 2–3 seconds
hard timeout: around 5 seconds
```

Important rule:

```text
Do not perform expensive full reindexing inside `engram start`.
```

If semantic index is unavailable or stale, Engram should fall back gracefully.

## 11. Local-First Constraint

Default retrieval should remain local.

Avoid as required dependencies:

```text
remote embedding APIs
remote vector databases
server-based retrieval systems
LLM relevance judges in normal path
```

The exact local model/vector storage can be selected later.

## 12. Debuggability

Retrieval quality must be inspectable.

Recommended command/flag:

```bash
engram start --debug-retrieval
engram memory related-to-task <task_id> --debug
```

Debug output should show:

```text
query text
retrieval mode
semantic candidates
FTS candidates
merged candidates
selected memories
scores/ranks
hidden count
latency breakdown
index freshness
```

## 13. Example Future `engram start` Output

```text
Project:
Engram — local-first, agent-agnostic memory system for coding agents.

Current phase:
Startup context redesign.
Goal: Make `engram start` produce useful project + task context without bloating output.

Current task:
Implement automatic task-memory retrieval in start output.
Acceptance: relevant memories are retrieved automatically, project guardrails remain visible, output stays under budget.

Project guardrails:
- Engram should remain local-first.
- Startup context should be compact and avoid prompt stuffing.
- Memory retrieval should be automatic; agents should not need to remember to search.

Relevant task memories:
- Lesson: Agents often skip explicit memory search, so `start` should surface relevant memory automatically.
- Decision: Use project/task memory scopes; do not add phase-memory scope initially.
- Lesson: Always-included memories can cause output growth if uncapped.

Next:
Implement a budgeted memory pack inside `engram start`.
```

## 14. Non-Goals

This design does not decide:

```text
exact embedding model
exact vector storage
exact FTS query syntax
exact rank fusion formula
schema migration details
implementation library
```

Those should be handled during implementation planning/Codex work.

## 15. Success Criteria

The design succeeds if:

```text
- `engram start` automatically surfaces useful memory
- project guardrails remain visible
- task memories are selected dynamically
- output stays bounded
- retrieval remains local-first
- agents no longer need to remember manual memory search
- retrieval behavior is debuggable
```
