# Engram Start Task Skill

Use this skill when the user asks to start or implement a specific Engram-managed task.

## Goal

Execute one scoped Engram task using the simplified MVP task loop.

The authoritative workflow source is `docs/adr/0002-workflow-mvp-simplification.md`.

## The Simplified MVP Loop

The core task execution loop consists of four sequential steps:
1. **Start**: Start or resume a task to obtain context.
2. **Implement**: Make focused, reviewable code changes.
3. **Verify**: Run verification checks locally to format, lint, test, and automatically stage changes on success.
4. **Finish and Commit**: Commit staged changes and push.

```text
start -> implement -> verify -> finish_and_commit
```

## Available Workflow Tools

- `engram_workflow_start`: Selects, resumes, or starts the next actionable task, returning a clear work order and context.
- `engram_workflow_verify`: Runs all required repo-local verification checks. If all checks pass, it automatically stages the changes via `git add -A` and marks the task as verified (`is_verified = true`).
- `engram_workflow_finish_and_commit` (deprecated transitional alias: `engram_workflow_finish`): Finalizes the task by committing the staged changes and pushing, then marks the task as done. It blocks if there are unstaged or untracked changes.

## Required Execution Steps

1. **Call Start**
   Invoke `engram_workflow_start` to activate the task and read the returned work order carefully.

2. **Understand and Plan**
   - Inspect only the files related to the active task.
   - For non-trivial tasks, produce a brief implementation plan and await user approval before writing code.

3. **Implement Changes**
   - Keep code modifications highly localized and scoped tightly to the task's acceptance criteria.
   - Do not perform unrelated refactoring.
   - Adhere to codebase rules (e.g., file sizes, public symbol limits, boundaries).

4. **Verify Locally**
   - Invoke `engram_workflow_verify` to run the project's repo-local quality gate checks (formatting, linting, and tests).
   - If verification fails, address only the failing items and retry.
   - Do not manually run `git add` unless explicitly instructed; a successful verify call stages the files for you.

5. **Finish and Commit**
   - Ensure the working tree is clean except for the staged files (verify command handles staging).
   - Call `engram_workflow_finish_and_commit` to commit and push the changes. Use `engram_workflow_finish` only if the alias is required by a transitional integration.
   - Stop. Do not automatically start the next task.

## Implementation Discipline

- **No Manual Staging**: Let `engram_workflow_verify` handle `git add` upon a successful test run.
- **Strict Scope**: Stay within the boundaries defined in the task context.
- **Clean State**: `finish_and_commit` will block if there are unstaged edits or untracked files. Make sure all intended changes are verified and staged, and untracked temporary files are cleaned up or gitignored.
- **No Per-Task Memory Gates**: Per-task memory review outcomes (e.g., `no_change`, `created`, `superseded`) are no longer required during the active task loop. Memory curation is done at the phase level.
