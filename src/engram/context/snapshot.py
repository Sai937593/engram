"""Snapshot context rendering."""

from engram.models.memory import Memory
from engram.models.project import Project
from engram.models.task import Task


def build_snapshot_context(project_id: str) -> str:
    """Export a full project snapshot as agent-readable Markdown."""
    project = Project.get(project_id)
    tasks = Task.list_by_project(project_id)
    memories = Memory.list_by_project(project_id)

    context: list[str] = []
    context.append(f"# PROJECT SNAPSHOT: {project.name} ({project.id})")
    if project.summary:
        context.append(f"Summary: {project.summary}")
    context.append(f"Status: {project.status}")

    context.append("\n## TASKS")
    for task in tasks:
        context.append(f"### [{task.status.upper()}] {task.title} ({task.id})")
        context.append(f"Priority: {task.priority}")
        if task.description:
            context.append(f"Description: {task.description}")
        if task.acceptance:
            context.append(f"Acceptance Criteria:\n{task.acceptance}")

    context.append("\n## MEMORIES")
    for memory in memories:
        context.append(f"### {memory.title} ({memory.type}) [{memory.id}]")
        if memory.tags:
            context.append(f"Tags: {', '.join(memory.tags)}")
        context.append(memory.content)

    return "\n".join(context)
