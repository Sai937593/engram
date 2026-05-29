"""Task context rendering."""

from engram.context_helpers.common import compact_text
from engram.models.memory import Memory
from engram.models.task import Task

TASK_CONTEXT_RELEVANT_FILE_LIMIT = 8
TASK_CONTEXT_RELEVANT_FILE_CHAR_LIMIT = 160


def _compact_path(path: str, char_limit: int) -> str:
    """Convert a path to compact ASCII with deterministic truncation."""
    compacted = compact_text(path)
    if not compacted or char_limit <= 0:
        return ""
    if len(compacted) <= char_limit:
        return compacted
    if char_limit <= 3:
        return compacted[:char_limit]
    return compacted[: char_limit - 3].rstrip() + "..."


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

    if task.relevant_files:
        context.append("\n## RELEVANT FILES")
        capped_paths = task.relevant_files[:TASK_CONTEXT_RELEVANT_FILE_LIMIT]
        for path in capped_paths:
            compacted_path = _compact_path(path, TASK_CONTEXT_RELEVANT_FILE_CHAR_LIMIT)
            if compacted_path:
                context.append(f"- {compacted_path}")
        hidden_count = max(0, len(task.relevant_files) - len(capped_paths))
        if hidden_count:
            context.append(f"... {hidden_count} additional relevant file path(s) hidden by cap.")

    if not hard_constraints_only:
        linked_memories = Memory.list_by_task(task_id)
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
