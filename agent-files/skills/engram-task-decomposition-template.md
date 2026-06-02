# Engram Task Decomposition Skill

Use this skill when the user asks to break a phase, plan, document, or feature into Engram tasks.

## Goal

Create executable Engram tasks that the simplified MVP workflow can start.

## Available Tools

Use phase and task tools such as:

- `engram_phase_list`
- `engram_phase_create`
- `engram_phase_start`
- `engram_phase_update`
- `engram_task_create`
- `engram_task_create_many` (for batch creation when available)
- `engram_task_list`
- `engram_task_get`
- `engram_task_update`

Do not use raw database access or write direct SQLite queries.

## Decomposition Rules

Create tasks that are:

- Small enough for one focused implementation session.
- Independently verifiable.
- Ordered by dependency.
- Explicit about files or search areas.
- Clear about acceptance criteria.
- Free of vague objectives like "improve workflow" without concrete behavior.

## Task Creation Shape

Create executable tasks using the simplified MVP fields. Required fields include:

- `title`: Short, action-oriented name.
- `objective`: Concise description of what the task accomplishes.
- `acceptance`: Clear criteria that must pass for the task to be done.
- `phase_id`: The ID of the parent phase.
- `verification`: Explicit verification instructions or commands.
- `relevant_files` or `search_hints`: Target files to modify or areas to inspect.

Newly created tasks start in the `open` status with `is_verified = false`.

Do not create weak placeholder tasks. If information is missing, either infer from the phase document or stop and ask the user.

## Naming convention

Use deterministic keys.

Plan key:
`plan-0003-workflow-standardization`

Phase key:
`ph01-planning-docs-and-naming`

Task key:
`t01-update-doc-structure`

Task plan path:
`.engram/task-plans/<plan_key>/<phase_key>/<task_key>/task-plan.md`

## Task Quality Checklist

Each task should answer:

- What must change?
- Where should the agent start looking?
- What is out of scope?
- How will the task be verified?
- Does it depend on another task?

## Output Style

After creating tasks, summarize:

- Phase created or used.
- Number of tasks created.
- Task order and dependency graph.
- Any assumptions or risks.
- Any tasks intentionally left out of scope.

Do not start implementation after decomposition unless the user explicitly asks.
