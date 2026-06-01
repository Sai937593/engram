# Engram Task Decomposition Skill

Use this skill when the user asks to break a phase, plan, document, or feature into Engram tasks.

This skill is written for the current redesign branch state. Do not call future simplified tools such as `engram_task_create_many` until they exist.

## Goal

Create executable Engram tasks that the current workflow can start.

## Current available tools

Use current phase/task tools such as:

- `engram_phase_list`
- `engram_phase_create`
- `engram_phase_start`
- `engram_phase_update`
- `engram_task_create`
- `engram_task_list`
- `engram_task_get`
- `engram_task_update`

Tool availability may vary by branch. If a listed tool is unavailable, use the closest existing Engram MCP tool rather than raw database access.

## Decomposition rules

Create tasks that are:

- small enough for one focused implementation session
- independently verifiable
- ordered by dependency
- explicit about files or search areas
- clear about acceptance criteria
- free of vague objectives like "improve workflow" without concrete behavior

## Current task creation shape

For the current redesign branch, create executable tasks using current fields.

Prefer:

- `title`
- `description`
- `acceptance`
- `relevant_files`
- `phase_id`
- `status = "ready"` when the task is intended to be executable

The current readiness validation expects meaningful `description`, `acceptance`, and `relevant_files`.

Do not create weak placeholder tasks. If information is missing, either infer from the phase document or stop and ask the user.

## Task quality checklist

Each task should answer:

- What must change?
- Where should the agent start looking?
- What is out of scope?
- How will the task be verified?
- Does it depend on another task?

If the current schema does not have a dedicated field for some of this information, include it in `description` or `acceptance`.

## Output style

After creating tasks, summarize:

- phase created or used
- number of tasks created
- task order
- any assumptions
- any tasks intentionally not created

Do not start implementation after decomposition unless the user explicitly asks.
