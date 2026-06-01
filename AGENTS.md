# Engram Agent Instructions

These instructions apply to work in this repository.

## Project role

Engram is a local-first project/workflow memory system for coding agents. Keep the implementation simple, explicit, and easy to inspect.

## Core engineering rules

- Prefer small, focused changes over broad rewrites.
- Preserve existing behavior unless the task explicitly asks to change it.
- Do not introduce abstractions before there is a concrete need.
- Keep agent-facing outputs compact and readable.
- Do not make agents write raw SQLite or inspect `.engram/memory.db` directly.
- Use Engram MCP tools or repository service code for task, phase, and memory operations.
- Do not hardcode `main` as a merge or transition target. Ask the user when a target branch is needed.
- Do not auto-start the next task after finishing a task.

## Python project rules

- Use `uv` for Python commands when available.
- Use existing project conventions before adding new dependencies.
- Keep public functions typed where practical.
- Keep tests close to the changed behavior.
- Avoid broad test rewrites unless the behavior being tested is intentionally changing.

## Verification expectations

For code changes, run the relevant local checks to verify that your changes have the desired effects and that the project builds and passes tests successfully before considering the work complete.

## Engram usage boundary

Do not force the Engram workflow on every interaction. Use Engram workflow only when the user asks to work on an Engram task, run a phase workflow, decompose work, or otherwise explicitly invokes Engram.
