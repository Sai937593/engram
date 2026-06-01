# Engram Start Task Skill

Use this skill when the user asks to start or implement a specific Engram-managed task.

This skill is written for the current redesign branch state. Do not call future simplified tools such as `engram_workflow_finish_and_commit`, `engram_memory_list`, `engram_memory_update_many`, or `engram_task_create_many` until they exist in the repository.

## Goal

Execute one scoped Engram task using the current MCP workflow.

## Current available workflow tools

Use these current tools:

- `engram_workflow_start`
- `engram_workflow_verify`
- `engram_workflow_finish`

The current branch also has task and memory tools. Use those only when needed.

## Required flow

1. Call `engram_workflow_start`.
2. Read the returned work order carefully.
3. Inspect only the files needed for the task.
4. Produce a short implementation plan.
5. Implement the scoped change.
6. Run focused checks if useful while editing.
7. Call `engram_workflow_verify`.
8. Fix any verification failures.
9. Repeat verification until it passes.
10. Complete the current memory-review gate using current tools.
11. Call `engram_workflow_finish`.
12. Stop. Do not auto-start another task.

## Current memory-review gate

The current redesign branch blocks `engram_workflow_finish` unless the task has a memory review outcome recorded.

This is transitional. Until the implementation removes the per-task memory-review gate, do this before finish:

1. Decide whether the task produced durable memory.
2. If not, record `no_change`.
3. If yes, use the existing memory tools to create or update memory as appropriate.
4. Record the task memory review outcome with the current task update tool.

Acceptable current outcomes are expected to include:

- `created`
- `superseded`
- `demoted`
- `archived`
- `deleted`
- `no_change`

Prefer `no_change` unless the task produced durable project knowledge.

Do not use Python or raw SQLite to perform memory review.

## Implementation discipline

- Stay inside the task scope.
- Do not make opportunistic unrelated refactors.
- Do not change project workflow design unless the task asks for it.
- Do not edit files after verification passes unless you rerun verification.
- Do not run `git add` manually as part of this skill unless the current tool output explicitly instructs you to do so.
- Let `engram_workflow_finish` handle commit behavior in the current implementation.

## Failure handling

If any Engram tool blocks:

1. Read the error and suggested fix.
2. Fix only the blocking issue.
3. Retry the same step.
4. If the block is about unclear product/design direction, stop and ask the user.

## Completion response

When finished, report only:

- task completed
- verification status
- commit/push status if provided by the tool
- any important caveat
