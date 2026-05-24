"""Task context rendering."""

from engram.context_helpers.common import compact_text
from engram.models.memory import Memory
from engram.models.task import Task


def build_task_context(task_id: str, hard_constraints_only: bool = False) -> str:
    """Generate focused context for a specific task."""
    task = Task.get(task_id)
    if not task:
        return "Task not found."

    context: list[str] = []
    context.append(f"# TASK: {task.title} ({task.id})")
    context.append(f"Status: {task.status} | Priority: {task.priority}")

    if task.phase_id:
        from engram.models.phase import Phase

        phase = Phase.get(task.phase_id)
        if phase:
            context.append("\n## PHASE")
            context.append(f"Phase: {phase.title} (Status: {phase.status})")
            if phase.description:
                context.append(f"Goal: {compact_text(phase.description)}")
            if phase.acceptance:
                context.append(f"Acceptance: {compact_text(phase.acceptance)}")
            if phase.evidence:
                context.append(f"Evidence: {compact_text(phase.evidence)}")
    elif task.phase:
        context.append("\n## PHASE")
        context.append(f"Phase: {task.phase}")

    if task.description:
        context.append(f"\nDescription: {task.description}")

    if task.acceptance:
        context.append(f"\nAcceptance Criteria:\n{task.acceptance}")

    if not hard_constraints_only:
        memories = Memory.list_by_project(task.project_id)
        linked_memories = [memory for memory in memories if memory.task_id == task_id]
        if linked_memories:
            context.append("\n## LINKED MEMORIES")
            for memory in linked_memories:
                context.append(f"### {memory.title} ({memory.type})")
                context.append(memory.content)

    constraints = Memory.list_by_type(task.project_id, "constraint")
    if hard_constraints_only:
        if constraints:
            context.append("\n## HARD CONSTRAINTS")
            for memory in constraints:
                context.append(f"### [CONSTRAINT] {memory.title}")
                context.append(memory.content)
        return "\n".join(context)

    lessons = Memory.list_by_type(task.project_id, "lesson")
    if constraints or lessons:
        context.append("\n## PROJECT KNOWLEDGE")
        for memory in constraints:
            context.append(f"### [CONSTRAINT] {memory.title}")
            context.append(memory.content)
        for memory in lessons:
            context.append(f"### [LESSON] {memory.title}")
            context.append(memory.content)

    return "\n".join(context)
