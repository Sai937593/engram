# Memory Review Skill

The Memory Review skill defines the process of evaluating, updating, and sanitizing the persistent project memory database (`.engram/memory.db`) at the completion of a development task. Its goal is to maintain a high-signal memory repository, preventing stale or redundant information from polluting future context windows.

---

## 1. Why Memory Review Matters

A clean memory store ensures that:
- AI agents in future sessions receive **precise, correct, and current** project guardrails and lessons.
- The context window remains small and high-signal, avoiding performance degradation or hallucinatory behavior.
- Outdated decisions, superseded lessons, and obsolete constraints are systematically retired.

---

## 2. Allowed Memory Review Outcomes

Every completed task must record a specific `memory_review_outcome` on the task before finishing. The six allowed outcomes are:

1. **`created`**
   - **When to use**: One or more new, highly relevant project-level memories (e.g. key design constraints, newly discovered environment details) were successfully added.
2. **`superseded`**
   - **When to use**: An existing memory (such as a previous design decision or a stale constraint) was updated or replaced by a new, more accurate one.
3. **`demoted`**
   - **When to use**: A project-level memory was downgraded to a lower scope (e.g. project scope to a single task scope) or demoted to a lower priority/level because its relevance has narrowed.
4. **`archived`**
   - **When to use**: A memory is no longer active but is preserved for historical auditing or context search rather than being completely deleted.
5. **`deleted`**
   - **When to use**: A memory was completely removed from the database because it was found to be redundant, incorrect, or irrelevant.
6. **`no_change`**
   - **When to use**: No new memories were created, and no existing memories were updated, demoted, archived, or deleted during this task.

---

## 3. Step-by-Step Memory Review Workflow

AI agents must perform the memory review using the following flow immediately after passing validation and before invoking the finish tool:

### Step 1: Verification
Ensure that the task's implementation is complete and all tests pass:
```bash
# Call verification tool (or CLI equivalent)
engram_workflow_verify
```

### Step 2: Audit Project Memories
Compare any memories created, updated, or deleted during this task. Assess their accuracy and signal-to-noise ratio:
- Check if new constraints or decisions should be stored via `engram_memory_create`.
- Check if old, outdated memories should be updated, superseded, or deleted.

### Step 3: Record the Outcome
Before calling the finish workflow, record the outcome of your audit on the active task:
```bash
# Update the active task with the chosen outcome
engram_task_update memory_review_outcome="<outcome>"
```
*Note: The `memory_review_outcome` must be one of the six allowed values: `created`, `superseded`, `demoted`, `archived`, `deleted`, or `no_change`.*

### Step 4: Finish and Commit
Once the outcome has been successfully saved to the tasks table, complete the workflow session:
```bash
# Complete the workflow session
engram_workflow_finish
```
