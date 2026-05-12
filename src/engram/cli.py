import click
import os
from rich.console import Console
from rich.table import Table
from engram.db import init_db
from engram.models.project import Project
from engram.models.task import Task
from engram.models.memory import Memory
from engram.models.session import Session
from engram.context import get_startup_context, get_task_context

console = Console()

@click.group()
def cli():
    """Engram — Agentic persistent memory system."""
    init_db()

@cli.command()
@click.option("--name", prompt="Project name", help="Human-readable project name")
@click.option("--id", help="Unique project ID (slug)")
@click.option("--summary", help="Short project summary")
def init(name, id, summary):
    """Initialize engram in the current repository."""
    cwd = os.getcwd()
    
    # Check if already registered
    existing = Project.find_by_repo_path(cwd)
    if existing:
        console.print(f"[yellow]Current directory is already bound to project:[/yellow] {existing.id} ({existing.name})")
        return

    if not id:
        # Simple slugify
        id = name.lower().replace(" ", "-")
    
    # Check if project ID already exists
    all_projects = Project.list_all()
    project = next((p for p in all_projects if p.id == id), None)
    
    if project:
        console.print(f"[yellow]Project '{id}' already exists. Binding current directory to it.[/yellow]")
        project.add_repo_path(cwd)
    else:
        Project.create(id, name, summary, repo_paths=[cwd])
        console.print(f"[green]Initialized project '{id}' and bound to current directory.[/green]")

@cli.group()
def project():
    """Manage projects."""
    pass

def get_current_project():
    cwd = os.getcwd()
    project = Project.find_by_repo_path(cwd)
    if not project:
        console.print("[red]Error:[/red] Current directory is not bound to any Engram project.")
        console.print("Run 'engram init' to register this repository.")
        exit(1)
    return project

@project.command(name="get")
def project_get():
    """Show current project details."""
    p = get_current_project()
    console.print(f"[cyan]ID:[/cyan] {p.id}")
    console.print(f"[cyan]Name:[/cyan] {p.name}")
    console.print(f"[cyan]Status:[/cyan] {p.status}")
    console.print(f"[cyan]Summary:[/cyan] {p.summary or 'N/A'}")
    console.print(f"[cyan]Repo Paths:[/cyan]")
    for path in p.repo_paths:
        console.print(f"  - {path}")

@project.command(name="update")
@click.option("--name", help="New project name")
@click.option("--summary", help="New project summary")
@click.option("--status", type=click.Choice(['active', 'paused', 'archived']), help="New project status")
def project_update(name, summary, status):
    """Update current project details."""
    p = get_current_project()
    if not any([name, summary, status]):
        console.print("[yellow]No updates provided.[/yellow]")
        return
    
    p.update(name=name, summary=summary, status=status)
    console.print(f"[green]Project '{p.id}' updated.[/green]")

@project.command(name="list")
def project_list():
    """List all registered projects."""
    projects = Project.list_all()
    if not projects:
        console.print("No projects registered.")
        return

    table = Table(title="Engram Projects")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Repo Paths")

    for p in projects:
        table.add_row(p.id, p.name, p.status, "\n".join(p.repo_paths))

    console.print(table)

# --- Task Commands ---

@cli.group()
def task():
    """Manage tasks."""
    pass

@task.command(name="add")
@click.argument("title")
@click.option("--description", help="Task description")
@click.option("--priority", type=click.Choice(['low', 'medium', 'high']), default='medium')
@click.option("--status", type=click.Choice(['backlog', 'todo', 'in-progress', 'done', 'blocked', 'cancelled']), default='backlog')
@click.option("--tags", help="Comma-separated tags")
def task_add(title, description, priority, status, tags):
    """Add a new task to the current project."""
    p = get_current_project()
    t = Task.create(
        project_id=p.id,
        title=title,
        description=description,
        priority=priority,
        status=status,
        tags=tags.split(",") if tags else []
    )
    console.print(f"[green]Task created with ID:[/green] {t.id}")

@task.command(name="list")
@click.option("--status", help="Filter by status")
def task_list(status):
    """List tasks for the current project."""
    p = get_current_project()
    tasks = Task.list_by_project(p.id)
    
    if status:
        tasks = [t for t in tasks if t.status == status]
        
    if not tasks:
        console.print("No tasks found.")
        return

    table = Table(title=f"Tasks for Project: {p.name}")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="green")
    table.add_column("Priority", style="yellow")
    
    for t in tasks:
        table.add_row(t.id, t.title, t.status, t.priority)
    
    console.print(table)

@task.command(name="update")
@click.argument("task_id")
@click.option("--field", help="Field to update (title, status, priority, description, tags)")
@click.option("--value", help="New value for the field")
def task_update(task_id, field, value):
    """Update a task field."""
    t = Task.get(task_id)
    if not t:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return
    
    if not field or not value:
        console.print("[yellow]Please provide both --field and --value.[/yellow]")
        return
    
    if field == 'tags':
        value = value.split(",")
    
    t.update(**{field: value})
    console.print(f"[green]Task '{task_id}' updated.[/green]")

@task.command(name="get")
@click.argument("task_id")
def task_get(task_id):
    """Show task details."""
    t = Task.get(task_id)
    if not t:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return
    
    console.print(f"[cyan]ID:[/cyan] {t.id}")
    console.print(f"[cyan]Title:[/cyan] {t.title}")
    console.print(f"[cyan]Status:[/cyan] {t.status}")
    console.print(f"[cyan]Priority:[/cyan] {t.priority}")
    console.print(f"[cyan]Description:[/cyan] {t.description or 'N/A'}")
    console.print(f"[cyan]Tags:[/cyan] {', '.join(t.tags)}")

# --- Memory Commands ---

@cli.group()
def memory():
    """Manage memories."""
    pass

@memory.command(name="add")
@click.argument("title")
@click.option("--content", prompt=True, help="Memory content")
@click.option("--type", default="note", help="Memory type (note, lesson, decision, snippet)")
@click.option("--tags", help="Comma-separated tags")
@click.option("--always-include", is_flag=True, help="Always include in context")
def memory_add(title, content, type, tags, always_include):
    """Add a new memory to the current project."""
    p = get_current_project()
    m = Memory.create(
        project_id=p.id,
        title=title,
        content=content,
        type=type,
        tags=tags.split(",") if tags else [],
        always_include=always_include
    )
    console.print(f"[green]Memory created with ID:[/green] {m.id}")

@memory.command(name="list")
def memory_list():
    """List memories for the current project."""
    p = get_current_project()
    memories = Memory.list_by_project(p.id)
    
    if not memories:
        console.print("No memories found.")
        return

    table = Table(title=f"Memories for Project: {p.name}")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Type", style="magenta")
    table.add_column("Tags", style="blue")
    
    for m in memories:
        table.add_row(m.id, m.title, m.type, ", ".join(m.tags))
    
    console.print(table)

@memory.command(name="search")
@click.argument("query")
def memory_search(query):
    """Search memories using FTS5."""
    results = Memory.search(query)
    if not results:
        console.print("No results found.")
        return
    
    table = Table(title=f"Search Results for: {query}")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Snippet")
    
    for m in results:
        # Simple snippet
        snippet = m.content[:50] + "..." if len(m.content) > 50 else m.content
        table.add_row(m.id, m.title, snippet)
    
    console.print(table)

# --- Session Commands ---

@cli.group()
def session():
    """Manage work sessions."""
    pass

@session.command(name="start")
@click.option("--goal", prompt="Session goal", help="What are you trying to accomplish?")
def session_start(goal):
    """Start a new work session."""
    p = get_current_project()
    active = Session.get_active(p.id)
    if active:
        console.print(f"[yellow]An active session already exists:[/yellow] {active.id} (Goal: {active.goal})")
        if click.confirm("Close it and start a new one?"):
            active.close(summary="Automatically closed to start new session.")
        else:
            return

    s = Session.create(project_id=p.id, goal=goal)
    console.print(f"[green]Session started with ID:[/green] {s.id}")

@session.command(name="close")
@click.option("--summary", prompt="Session summary", help="What did you accomplish?")
@click.option("--next-steps", help="What are the next steps?")
def session_close(summary, next_steps):
    """Close the active work session."""
    p = get_current_project()
    s = Session.get_active(p.id)
    if not s:
        console.print("[red]Error:[/red] No active session found for this project.")
        return
    
    s.close(summary=summary, next_steps=next_steps)
    console.print(f"[green]Session '{s.id}' closed.[/green]")

@session.command(name="list")
@click.option("--all", is_flag=True, help="List all sessions (including closed)")
def session_list(all):
    """List sessions for the current project."""
    p = get_current_project()
    sessions = Session.list_by_project(p.id)
    
    if not all:
        sessions = [s for s in sessions if s.status == 'open']
        
    if not sessions:
        console.print("No sessions found.")
        return

    table = Table(title=f"Sessions for Project: {p.name}")
    table.add_column("ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Goal", style="white")
    table.add_column("Started At", style="yellow")
    
    for s in sessions:
        table.add_row(s.id, s.status, s.goal or "N/A", s.started_at)
    
    console.print(table)

# --- Context Commands ---

@cli.group()
def context():
    """Generate context for agents."""
    pass

@context.command(name="startup")
def context_startup():
    """Generate project startup context."""
    p = get_current_project()
    ctx = get_startup_context(p.id)
    console.print(ctx)

@context.command(name="task")
@click.argument("task_id")
def context_task(task_id):
    """Generate task-specific context."""
    ctx = get_task_context(task_id)
    console.print(ctx)

def main():
    cli()

if __name__ == "__main__":
    main()
