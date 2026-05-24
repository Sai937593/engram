"""Handoff context rendering."""

from engram.models.memory import Memory
from engram.models.project import Project
from engram.models.task import Task


def build_handoff_context(project_id: str) -> str:
    """Generate a project handoff document for another agent or human."""
    project = Project.get(project_id)
    tasks = Task.list_by_project(project_id)
    constraints = Memory.list_by_type(project_id, "constraint")
    lessons = Memory.list_by_type(project_id, "lesson")
    decisions = Memory.list_by_type(project_id, "decision")

    all_memories = Memory.list_by_project(project_id)
    typed_ids = {memory.id for memory in constraints + lessons + decisions}
    other_important = [
        memory for memory in all_memories if memory.always_include and memory.id not in typed_ids
    ]

    context: list[str] = []
    context.append(f"# PROJECT HANDOFF: {project.name}")
    if project.summary:
        context.append(f"Context: {project.summary}")

    context.append("\n## ACTIVE TASKS")
    active_tasks = [task for task in tasks if task.status in ("todo", "in-progress", "blocked")]
    for task in active_tasks:
        context.append(f"### {task.title} ({task.id})")
        context.append(f"Status: {task.status} | Priority: {task.priority}")
        if task.description:
            context.append(f"Description: {task.description}")

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

    if other_important:
        context.append("\n## CRITICAL CONTEXT")
        for memory in other_important:
            context.append(f"### {memory.title} ({memory.type})")
            context.append(memory.content)

    context.append("\n## NEXT STEPS")
    context.append("Refer to active tasks above.")

    return "\n".join(context)
