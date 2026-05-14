from engram.models.memory import Memory
from engram.models.project import Project
from engram.models.session import Session
from engram.models.task import Task


def get_startup_context(project_id: str) -> str:
    """Generate a compact, agent-optimized startup context string."""
    project = Project.get(project_id)
    active_session = Session.get_active(project_id)
    last_closed = Session.get_latest_closed(project_id)

    # Fetch typed memories up-front
    constraints = Memory.list_by_type(project_id, "constraint")
    lessons = Memory.list_by_type(project_id, "lesson")
    decisions = Memory.list_by_type(project_id, "decision")
    # Other always-include memories (notes, snippets) that don't fit a typed bucket
    all_memories = Memory.list_by_project(project_id)
    typed_ids = {m.id for m in constraints + lessons + decisions}
    other_always_include = [m for m in all_memories if m.always_include and m.id not in typed_ids]

    context = []
    context.append(f"# PROJECT: {project.name}")
    if project.summary:
        context.append(f"Summary: {project.summary}")

    if last_closed:
        context.append(
            f"\n## LAST CHECKPOINT ({last_closed.id},"
            f" {last_closed.closed_at[:10] if last_closed.closed_at else 'unknown'})"
        )
        if last_closed.summary:
            context.append(f"Done: {last_closed.summary}")
        if last_closed.next_steps:
            context.append(f"Next: {last_closed.next_steps}")

    if active_session:
        context.append(f"\n## ACTIVE SESSION: {active_session.id}")
        context.append(f"Goal: {active_session.goal}")

    # --- Constraints (hard rules — always read FIRST) ---
    if constraints:
        context.append("\n## CONSTRAINTS")
        for m in constraints:
            context.append(f"### {m.title}")
            context.append(m.content)

    # --- Lessons Learned (solved problems — don't re-solve) ---
    if lessons:
        context.append("\n## LESSONS LEARNED")
        for m in lessons:
            context.append(f"### {m.title}")
            context.append(m.content)

    # --- Key Decisions (architectural rationale) ---
    if decisions:
        context.append("\n## KEY DECISIONS")
        for m in decisions:
            context.append(f"### {m.title}")
            context.append(m.content)

    # --- Other always-include memories ---
    if other_always_include:
        context.append("\n## KEY MEMORIES")
        for m in other_always_include:
            context.append(f"### {m.title} ({m.type})")
            context.append(m.content)

    # --- Task state ---
    tasks = Task.list_by_project(project_id)
    counts = Task.count_by_status(project_id)
    total = sum(counts.values())
    todo_tasks = [t for t in tasks if t.status in ("todo", "in-progress")]

    if todo_tasks:
        context.append("\n## ACTIVE TASKS")
        for t in todo_tasks[:5]:
            context.append(f"- [{t.status}] {t.title} ({t.id})")

    pending_count = len([t for t in tasks if t.status not in ("done", "cancelled")])
    context.append(f"\nPending tasks: {pending_count}")

    # Phase-gap guidance — actionable messaging when no work is queued
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
            '  engram task add "<next task>"  — to continue\n'
            "  engram project update --status archived  — to close"
        )

    context.append(
        "Tip: use 'engram task get <id>' for full detail,"
        " 'engram memory search <topic>' to find context"
    )

    return "\n".join(context)


def get_task_context(task_id: str) -> str:
    """Generate focused context for a specific task, including project-wide knowledge."""
    task = Task.get(task_id)
    if not task:
        return "Task not found."

    context = []
    context.append(f"# TASK: {task.title} ({task.id})")
    context.append(f"Status: {task.status} | Priority: {task.priority}")
    if task.description:
        context.append(f"\nDescription: {task.description}")

    if task.acceptance:
        context.append(f"\nAcceptance Criteria:\n{task.acceptance}")

    # Memories linked directly to this task
    memories = Memory.list_by_project(task.project_id)
    linked_memories = [m for m in memories if m.task_id == task_id]
    if linked_memories:
        context.append("\n## LINKED MEMORIES")
        for m in linked_memories:
            context.append(f"### {m.title} ({m.type})")
            context.append(m.content)

    # Project-wide knowledge every agent needs before touching any task
    constraints = Memory.list_by_type(task.project_id, "constraint")
    lessons = Memory.list_by_type(task.project_id, "lesson")
    if constraints or lessons:
        context.append("\n## PROJECT KNOWLEDGE")
        for m in constraints:
            context.append(f"### [CONSTRAINT] {m.title}")
            context.append(m.content)
        for m in lessons:
            context.append(f"### [LESSON] {m.title}")
            context.append(m.content)

    return "\n".join(context)


def get_snapshot_context(project_id: str) -> str:
    """Export a full project snapshot as agent-readable Markdown."""
    project = Project.get(project_id)
    tasks = Task.list_by_project(project_id)
    memories = Memory.list_by_project(project_id)
    sessions = Session.list_by_project(project_id)

    context = []
    context.append(f"# PROJECT SNAPSHOT: {project.name} ({project.id})")
    if project.summary:
        context.append(f"Summary: {project.summary}")
    context.append(f"Status: {project.status}")

    context.append("\n## TASKS")
    for t in tasks:
        context.append(f"### [{t.status.upper()}] {t.title} ({t.id})")
        context.append(f"Priority: {t.priority}")
        if t.description:
            context.append(f"Description: {t.description}")
        if t.acceptance:
            context.append(f"Acceptance Criteria:\n{t.acceptance}")

    context.append("\n## MEMORIES")
    for m in memories:
        context.append(f"### {m.title} ({m.type}) [{m.id}]")
        if m.tags:
            context.append(f"Tags: {', '.join(m.tags)}")
        context.append(m.content)

    context.append("\n## SESSION HISTORY")
    for s in sessions:
        context.append(f"- **{s.id}** ({s.status}): {s.goal}")
        if s.summary:
            context.append(f"  Summary: {s.summary}")

    return "\n".join(context)


def get_handoff_context(project_id: str) -> str:
    """Generate a project handoff document for another agent or human."""
    project = Project.get(project_id)
    active_session = Session.get_active(project_id)
    last_closed = Session.get_latest_closed(project_id)
    tasks = Task.list_by_project(project_id)
    constraints = Memory.list_by_type(project_id, "constraint")
    lessons = Memory.list_by_type(project_id, "lesson")
    decisions = Memory.list_by_type(project_id, "decision")
    # Other important memories
    all_memories = Memory.list_by_project(project_id)
    typed_ids = {m.id for m in constraints + lessons + decisions}
    other_important = [m for m in all_memories if m.always_include and m.id not in typed_ids]

    context = []
    context.append(f"# PROJECT HANDOFF: {project.name}")
    if project.summary:
        context.append(f"Context: {project.summary}")

    if active_session:
        context.append("\n## CURRENT GOAL")
        context.append(active_session.goal)

    context.append("\n## ACTIVE TASKS")
    active_tasks = [t for t in tasks if t.status in ("todo", "in-progress", "blocked")]
    for t in active_tasks:
        context.append(f"### {t.title} ({t.id})")
        context.append(f"Status: {t.status} | Priority: {t.priority}")
        if t.description:
            context.append(f"Description: {t.description}")

    if constraints:
        context.append("\n## CONSTRAINTS")
        for m in constraints:
            context.append(f"### {m.title}")
            context.append(m.content)

    if lessons:
        context.append("\n## LESSONS LEARNED")
        for m in lessons:
            context.append(f"### {m.title}")
            context.append(m.content)

    if decisions:
        context.append("\n## KEY DECISIONS")
        for m in decisions:
            context.append(f"### {m.title}")
            context.append(m.content)

    if other_important:
        context.append("\n## CRITICAL CONTEXT")
        for m in other_important:
            context.append(f"### {m.title} ({m.type})")
            context.append(m.content)

    context.append("\n## NEXT STEPS")
    if last_closed and last_closed.next_steps:
        context.append(last_closed.next_steps)
    else:
        context.append("Refer to active tasks above.")

    return "\n".join(context)
