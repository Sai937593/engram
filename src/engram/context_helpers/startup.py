"""Startup context rendering."""

from engram.models.memory import Memory
from engram.models.project import Project
from engram.models.task import Task


def build_startup_context(project_id: str) -> str:
    """Generate a compact, agent-optimized startup context string."""
    project = Project.get(project_id)

    constraints = Memory.list_by_type(project_id, "constraint")
    lessons = Memory.list_by_type(project_id, "lesson")
    decisions = Memory.list_by_type(project_id, "decision")
    all_memories = Memory.list_by_project(project_id)
    typed_ids = {memory.id for memory in constraints + lessons + decisions}
    other_always_include = [
        memory for memory in all_memories if memory.always_include and memory.id not in typed_ids
    ]

    context: list[str] = []
    context.append(f"# PROJECT: {project.name}")
    if project.summary:
        context.append(f"Summary: {project.summary}")

    if constraints:
        context.append("\n## CONSTRAINTS")
        for memory in constraints:
            context.append(f"### {memory.title}")
            context.append(memory.content)

    if lessons:
        context.append("\n## LESSONS LEARNED")
        for memory in lessons:
            context.append(f"### {memory.title}")
            context.append(memory.content)

    if decisions:
        context.append("\n## KEY DECISIONS")
        for memory in decisions:
            context.append(f"### {memory.title}")
            context.append(memory.content)

    if other_always_include:
        context.append("\n## KEY MEMORIES")
        for memory in other_always_include:
            context.append(f"### {memory.title} ({memory.type})")
            context.append(memory.content)

    tasks = Task.list_by_project(project_id)
    counts = Task.count_by_status(project_id)
    total = sum(counts.values())
    todo_tasks = [task for task in tasks if task.status in ("todo", "in-progress")]

    if todo_tasks:
        context.append("\n## ACTIVE TASKS")
        for task in todo_tasks:
            context.append(f"- [{task.status}] {task.title} ({task.id})")

    pending_count = len([task for task in tasks if task.status not in ("done", "cancelled")])
    context.append(f"\nPending tasks: {pending_count}")

    if total == 0:
        context.append(
            "\n## STATUS: NO TASKS DEFINED\n"
            "The next phase has not been planned. Before writing any code, ask the user\n"
            "what the next phase of work should be, then add tasks:\n"
            '  engram task add "<task title>" --phase "Phase N" --priority high'
        )
    elif pending_count == 0:
        context.append(
            "\n## STATUS: PHASE COMPLETE\n"
            f"All {total} task(s) are done or cancelled. Confirm with the user whether\n"
            "to plan the next phase or mark the project complete:\n"
            '  engram task add "<next task>"  -- to continue\n'
            "  engram project update --status archived  -- to close"
        )

    context.append(
        "Tip: use 'engram task get <id>' for full detail,"
        " 'engram memory search <topic>' to find context"
    )

    return "\n".join(context)
