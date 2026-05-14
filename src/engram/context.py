from engram.models.project import Project
from engram.models.session import Session
from engram.models.memory import Memory
from engram.models.task import Task

def get_startup_context(project_id):
    project = Project.get(project_id)
    active_session = Session.get_active(project_id)
    last_closed = Session.get_latest_closed(project_id)
    always_include = Memory.list_always_include(project_id)
    
    context = []
    context.append(f"# PROJECT: {project.name}")
    if project.summary:
        context.append(f"Summary: {project.summary}")
    
    if last_closed:
        context.append(f"\n## LAST CHECKPOINT ({last_closed.id}, {last_closed.closed_at[:10] if last_closed.closed_at else 'unknown'})")
        if last_closed.summary:
            context.append(f"Done: {last_closed.summary}")
        if last_closed.next_steps:
            context.append(f"Next: {last_closed.next_steps}")

    if active_session:
        context.append(f"\n## ACTIVE SESSION: {active_session.id}")
        context.append(f"Goal: {active_session.goal}")
    
    if always_include:
        context.append("\n## KEY MEMORIES")
        for m in always_include:
            context.append(f"### {m.title} ({m.type})")
            context.append(m.content)
            
    # Active tasks (todo + in-progress)
    tasks = Task.list_by_project(project_id)
    todo_tasks = [t for t in tasks if t.status in ['todo', 'in-progress']]
    if todo_tasks:
        context.append("\n## ACTIVE TASKS")
        for t in todo_tasks[:5]:
            context.append(f"- [{t.status}] {t.title} ({t.id})")

    pending_count = len([t for t in tasks if t.status not in ['done', 'cancelled']])
    context.append(f"\nPending tasks: {pending_count}")
    context.append("Tip: use 'engram task get <id>' for full detail, 'engram memory search <topic>' to find context")
            
    return "\n".join(context)

def get_task_context(task_id):
    task = Task.get(task_id)
    if not task:
        return "Task not found."
        
    project = Project.get(task.project_id)
    
    context = []
    context.append(f"# TASK: {task.title} ({task.id})")
    context.append(f"Status: {task.status} | Priority: {task.priority}")
    if task.description:
        context.append(f"\nDescription: {task.description}")
        
    if task.acceptance:
        context.append(f"\nAcceptance Criteria:\n{task.acceptance}")
        
    # Find memories linked to this task
    memories = Memory.list_by_project(task.project_id)
    linked_memories = [m for m in memories if m.task_id == task_id]
    
    if linked_memories:
        context.append("\n## LINKED MEMORIES")
        for m in linked_memories:
            context.append(f"### {m.title} ({m.type})")
            context.append(m.content)
            
    return "\n".join(context)

def get_snapshot_context(project_id):
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

def get_handoff_context(project_id):
    project = Project.get(project_id)
    active_session = Session.get_active(project_id)
    last_closed = Session.get_latest_closed(project_id)
    tasks = Task.list_by_project(project_id)
    # Get important memories (lessons, decisions, always_include)
    memories = Memory.list_by_project(project_id)
    important_memories = [m for m in memories if m.type in ['lesson', 'decision'] or m.always_include]
    
    context = []
    context.append(f"# PROJECT HANDOFF: {project.name}")
    if project.summary:
        context.append(f"Context: {project.summary}")
        
    if active_session:
        context.append(f"\n## CURRENT GOAL")
        context.append(active_session.goal)
        
    context.append("\n## ACTIVE TASKS")
    active_tasks = [t for t in tasks if t.status in ['todo', 'in-progress', 'blocked']]
    for t in active_tasks:
        context.append(f"### {t.title} ({t.id})")
        context.append(f"Status: {t.status} | Priority: {t.priority}")
        if t.description:
            context.append(f"Description: {t.description}")
            
    context.append("\n## CRITICAL CONTEXT")
    for m in important_memories:
        context.append(f"### {m.title} ({m.type})")
        context.append(m.content)
        
    context.append("\n## NEXT STEPS")
    # Use the last closed session's next_steps — the active session never has these populated
    if last_closed and last_closed.next_steps:
        context.append(last_closed.next_steps)
    else:
        context.append("Refer to active tasks above.")
        
    return "\n".join(context)
