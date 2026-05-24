# Engram Memory Retrieval and Startup Context Design Spec

## 1. Purpose

This design defines how Engram should automatically surface relevant memory in
`engram start`.

The goal is to prevent agents from skipping memory search while keeping startup
context useful, compact, local-first, and low-friction.

This design assumes the first-class Phase -> Task hierarchy exists:

```text
Project
  -> Phase
       -> Task
```

## 2. Core Design Decision

Use two memory scopes:

```text
project
task
```

Do not introduce phase-memory scope initially. Phase is planning context, not a
separate memory plane.

## 3. Memory Scope Contract

### Project Memory

Project memory is durable context for the whole project. It is used to keep
agents aligned with product identity, architecture, constraints, and persistent
operating rules.

Project memories support a required `level`:

```text
L0 = project identity / core principles
L1 = non-negotiable constraints
L2 = architecture decisions
L3 = situational project knowledge
```

Initial migration/defaulting rules:

```text
- existing type=constraint memories -> scope=project, level=L1
- existing type=decision memories -> scope=project, level=L2
- existing type=lesson memories -> scope=project, level=L3 unless linked to a task
- existing always_include memories -> scope=project, level=L1 if no better mapping exists
- existing note/snippet memories -> scope=task when task_id is set, otherwise scope=project, level=L3
```

Project memory validation:

```text
- scope=project requires level in L0, L1, L2, L3
- scope=project may not require task_id
- level is shown in list/detail/debug output
```

### Task Memory

Task memory is reusable work-derived knowledge that may help future tasks. It is
not limited to the task that created it.

Task memories are flat chunks:

```text
- scope=task
- level must be null/empty
- task_id is optional
```

`task_id` means "originating task" or "directly linked task", not "only relevant
to this task". Retrieval should search across task-scope memories for the
current project and may boost memories whose `task_id` matches the active task.

Examples:

```text
- previous bug fix lesson
- useful debugging note
- prior implementation decision
- reusable command/snippet
- trap discovered while working on a similar task
```

## 4. Memory CLI Contract

Memory commands should expose the storage contract directly.

Recommended creation flags:

```bash
engram memory add "<title>" --content "<content>" --type lesson --scope task
engram memory add "<title>" --content "<content>" --type constraint --scope project --level L1
engram memory add "<title>" --content "<content>" --scope task --task-id <task-id>
```

Recommended update fields:

```bash
engram memory update <memory-id> --field scope --value task
engram memory update <memory-id> --field level --value L2
engram memory update <memory-id> --field task_id --value <task-id>
```

Validation behavior:

```text
- reject unknown scope values
- reject unknown levels
- reject level on scope=task
- reject scope=project without level
- reject task_id that does not exist in the current project
- preserve current typed shortcuts such as `engram lesson add`
```

Typed shortcut defaults:

```text
engram constraint add -> scope=project, level=L1, always_include=true by default
engram decision add   -> scope=project, level=L2, always_include=true by default initially
engram lesson add     -> scope=task by default unless --project/--level is provided
engram snippet add    -> scope=task by default, always_include=false by default
```

## 5. Startup Context Philosophy

`engram start` should become the primary context router. It should not rely on
the agent to remember:

```bash
engram memory search ...
```

Instead, `engram start` should automatically include a relevant memory pack.

Recommended startup structure:

```text
1. Project frame
2. Current phase frame
3. Current/next task frame
4. Project guardrails
5. Task-relevant memory pack
6. Next action
```

Implementation ownership:

```text
- create a unified startup context builder used by `engram start`
- keep task-only context helpers for `engram task get` / focused task context
- do not leave `engram start` split between startup context and hard-constraints-only task context
```

## 6. Output Budget

Recommended default:

```text
target: 1,500-2,000 tokens
hard max: 3,000 tokens
```

Implementation should use deterministic budget enforcement. A character budget
is acceptable for v1 because it is easy to test and does not require tokenizer
dependencies.

Suggested approximation:

```text
1 token ~= 4 characters
target: 6,000-8,000 characters
hard max: 12,000 characters
```

Suggested allocation:

```text
Project frame:              600-1,000 chars
Current phase:              600-1,200 chars
Current task:               1,000-1,600 chars
Project guardrails:         1,200-2,000 chars
Task-relevant memories:     2,800-4,800 chars
Next action:                400-800 chars
```

The goal is not to use the full model context window. The goal is to provide a
dense, high-signal startup pack.

## 7. Project Memory Inclusion Policy

Project memories should not all be dumped every time.

Initial policy:

```text
L0: always included, compacted to budget
L1: included by default, capped at 3-6 items
L2: included only if relevant or if space allows
L3: omitted from guardrails; eligible for retrieval only when useful
```

For v1, include:

```text
- compact L0 project identity if present
- up to 6 L1 project guardrails
```

## 8. Task Memory Retrieval

Task memories should be retrieved dynamically from the active/next task.

Query source:

```text
task.title
task.description
task.acceptance
phase.title
phase.description
phase.acceptance
task.tags
```

Avoid dumping large evidence logs into the query. Evidence may be summarized or
omitted in v1.

Retrieval should ultimately use two independent channels:

```text
semantic retrieval
keyword/FTS retrieval
```

Correct long-term shape:

```text
Semantic retrieval \
                    -> dedupe -> fuse/rerank -> select -> pack
FTS retrieval      /
```

Do not implement semantic retrieval before the local embedding/storage choice is
made. The first implementation milestone should use FTS retrieval only because
SQLite FTS already exists in the project.

## 9. Ranking and Fusion

High-level requirement:

```text
Task memory retrieval should combine exact keyword precision first, then add
semantic recall when a local semantic index is available.
```

Recommended delivery order:

```text
v1: FTS retrieval + task_id/type/tag boosts + budgeted packing
v2: local semantic index abstraction and reindex command
v3: semantic + FTS fusion
v4: optional reranker only if evidence shows it is needed
```

## 10. Top-K and Selection Policy

Do not use a fixed K as the only control.

Use:

```text
character/token budget
relevance threshold
deduplication
maximum K
```

Recommended task memory selection:

```text
preferred: 5-8 memories
hard max: 10 memories
section budget: 2,800-4,800 characters
```

Project memory selection:

```text
L0: always compacted
L1: 3-6 items
L2/L3: conditional/future
```

## 11. Latency Policy

Because `engram start` may be run through a session-start hook, some latency is
acceptable.

Recommended budget:

```text
ideal: under 1.5 seconds
acceptable: 2-3 seconds
hard timeout: around 5 seconds
```

Important rule:

```text
Do not perform expensive full reindexing inside `engram start`.
```

If an optional semantic index is unavailable or stale, Engram should fall back to
FTS without failing startup.

## 12. Local-First Constraint

Default retrieval must remain local.

Avoid as required dependencies:

```text
remote embedding APIs
remote vector databases
server-based retrieval systems
LLM relevance judges in normal path
```

Any semantic retrieval implementation must use a local-first abstraction with a
clear fallback path.

## 13. Debuggability

Retrieval quality must be inspectable.

Recommended command/flag:

```bash
engram start --debug-retrieval
engram memory related-to-task <task-id> --debug
```

Debug output should show:

```text
query text
retrieval mode
FTS candidates
semantic candidates when available
merged candidates when fusion exists
selected memories
scores/ranks/boosts
hidden count
latency breakdown
index freshness when semantic retrieval exists
budget used and truncated items
```

## 14. Example Future `engram start` Output

```text
Project:
Engram - local-first, agent-agnostic memory system for coding agents.

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
Use the startup context to implement the current task. If retrieval debug is needed, run:
  engram start --debug-retrieval
```

## 15. Non-Goals

Initial retrieval work does not include:

```text
phase-memory scope
remote embedding APIs as default
required vector database server
LLM-based relevance judge
cross-encoder reranker
complex per-dimension relevance scoring
automatic full reindex inside start
semantic retrieval before local storage/model choices are made
```

## 16. Success Criteria

The design succeeds if:

```text
- `engram start` automatically surfaces useful memory
- project guardrails remain visible
- task memories are selected dynamically
- output stays bounded
- retrieval remains local-first
- agents no longer need to remember manual memory search
- retrieval behavior is debuggable
- the first implementation path can ship value with FTS before semantic retrieval
```
