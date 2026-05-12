from engram.models.project import Project
from engram.models.session import Session
from engram.models.memory import Memory
from engram.models.task import Task

def get_startup_context(project_id):
    project = Project.get(project_id)
    active_session = Session.get_active(project_id)
    always_include = Memory.list_always_include(project_id)
    
    context = []
    context.append(f"# PROJECT: {project.name}")
    if project.summary:
        context.append(f"Summary: {project.summary}")
    
    if active_session:
        context.append(f"\n## ACTIVE SESSION: {active_session.id}")
        context.append(f"Goal: {active_session.goal}")
    
    if always_include:
        context.append("\n## KEY MEMORIES")
        for m in always_include:
            context.append(f"### {m.title} ({m.type})")
            context.append(m.content)
            
    # Recent tasks (last 5)
    tasks = Task.list_by_project(project_id)
    todo_tasks = [t for t in tasks if t.status in ['todo', 'in-progress']]
    if todo_tasks:
        context.append("\n## ACTIVE TASKS")
        for t in todo_tasks[:5]:
            context.append(f"- [{t.status}] {t.title} ({t.id})")
            
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
