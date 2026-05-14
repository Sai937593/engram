import os

import click
from rich.console import Console
from rich.table import Table

from engram.context import (
    get_handoff_context,
    get_snapshot_context,
    get_startup_context,
    get_task_context,
)
from engram.db import init_db
from engram.models.memory import Memory
from engram.models.project import Project
from engram.models.session import Session
from engram.models.task import Task

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
        console.print(
            f"[yellow]Current directory is already bound to project:[/yellow] {existing.id} ({existing.name})"
        )
        return

    if not id:
        # Simple slugify
        id = name.lower().replace(" ", "-")

    # Check if project ID already exists
    all_projects = Project.list_all()
    project = next((p for p in all_projects if p.id == id), None)

    if project:
        console.print(
            f"[yellow]Project '{id}' already exists. Binding current directory to it.[/yellow]"
        )
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
        raise SystemExit(1)
    return project


@project.command(name="get")
def project_get():
    """Show current project details."""
    p = get_current_project()
    console.print(f"[cyan]ID:[/cyan] {p.id}")
    console.print(f"[cyan]Name:[/cyan] {p.name}")
    console.print(f"[cyan]Status:[/cyan] {p.status}")
    console.print(f"[cyan]Summary:[/cyan] {p.summary or 'N/A'}")
    console.print("[cyan]Repo Paths:[/cyan]")
    for path in p.repo_paths:
        console.print(f"  - {path}")


@project.command(name="update")
@click.option("--name", help="New project name")
@click.option("--summary", help="New project summary")
@click.option(
    "--status", type=click.Choice(["active", "paused", "archived"]), help="New project status"
)
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

    table = Table(title="Engram Projects", header_style="bold magenta", border_style="cyan")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Repo Paths", style="dim")

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
@click.option(
    "--priority", type=click.Choice(["low", "medium", "high", "critical"]), default="medium"
)
@click.option(
    "--status",
    type=click.Choice(["todo", "in-progress", "done", "blocked", "cancelled"]),
    default="todo",
)
@click.option("--tags", help="Comma-separated tags")
@click.option("--acceptance", help="Acceptance criteria")
@click.option("--phase", help="Project phase")
def task_add(title, description, priority, status, tags, acceptance, phase):
    """Add a new task to the current project."""
    p = get_current_project()
    t = Task.create(
        project_id=p.id,
        title=title,
        description=description,
        priority=priority,
        status=status,
        tags=tags.split(",") if tags else [],
        acceptance=acceptance,
        phase=phase,
    )
    console.print(f"[green]Task created with ID:[/green] {t.id}")


@task.command(name="start")
@click.argument("task_id")
def task_start(task_id):
    """Mark a task as in-progress (claim it)."""
    t = Task.get(task_id)
    if not t:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return
    if t.status == "in-progress":
        console.print(f"[yellow]Task '{task_id}' is already in-progress.[/yellow]")
        return
    t.update(status="in-progress")
    console.print(f"[green]Task '{task_id}' marked as in-progress.[/green]")


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

    table = Table(
        title=f"Tasks for Project: {p.name}", header_style="bold green", border_style="green"
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Status", style="bold green")
    table.add_column("Priority", style="yellow")

    for t in tasks:
        status_style = "green"
        if t.status == "blocked":
            status_style = "red"
        elif t.status == "done":
            status_style = "blue"
        elif t.status == "in-progress":
            status_style = "yellow"

        priority_style = "yellow"
        if t.priority == "high":
            priority_style = "bold red"

        table.add_row(
            t.id,
            t.title,
            f"[{status_style}]{t.status}[/{status_style}]",
            f"[{priority_style}]{t.priority}[/{priority_style}]",
        )

    console.print(table)


VALID_TASK_FIELDS = {
    "title",
    "status",
    "priority",
    "description",
    "tags",
    "acceptance",
    "phase",
    "evidence",
}
VALID_TASK_STATUSES = {"todo", "in-progress", "done", "blocked", "cancelled"}
VALID_TASK_PRIORITIES = {"low", "medium", "high", "critical"}


@task.command(name="update")
@click.argument("task_id")
@click.option(
    "--field",
    help="Field to update (title, status, priority, description, tags, acceptance, phase, evidence)",
)
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

    if field not in VALID_TASK_FIELDS:
        console.print(
            f"[red]Error:[/red] Unknown field '{field}'. Valid fields: {', '.join(sorted(VALID_TASK_FIELDS))}"
        )
        return

    if field == "status" and value not in VALID_TASK_STATUSES:
        console.print(
            f"[red]Error:[/red] Invalid status '{value}'. Valid: {', '.join(sorted(VALID_TASK_STATUSES))}"
        )
        return

    if field == "priority" and value not in VALID_TASK_PRIORITIES:
        console.print(
            f"[red]Error:[/red] Invalid priority '{value}'. Valid: {', '.join(sorted(VALID_TASK_PRIORITIES))}"
        )
        return

    # Soft warning on terminal → active status transition
    terminal_statuses = {"done", "cancelled"}
    if field == "status" and t.status in terminal_statuses and value not in terminal_statuses:
        console.print(
            f"[yellow]⚠ Warning: transitioning '{task_id}' from '{t.status}' → '{value}'. Continuing...[/yellow]"
        )

    if field == "tags":
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
    console.print(f"[cyan]Phase:[/cyan] {t.phase or 'N/A'}")
    console.print(f"[cyan]Description:[/cyan] {t.description or 'N/A'}")
    console.print(f"[cyan]Acceptance Criteria:[/cyan]\n{t.acceptance or 'N/A'}")
    console.print(f"[cyan]Evidence / Notes:[/cyan]\n{t.evidence or 'N/A'}")
    console.print(f"[cyan]Tags:[/cyan] {', '.join(t.tags)}")


@task.command(name="done")
@click.argument("task_id")
@click.option("--evidence", help="Evidence of completion (tests, PR, etc.)")
def task_done(task_id, evidence):
    """Mark a task as done (optionally record evidence)."""
    t = Task.get(task_id)
    if not t:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return

    updates = {"status": "done"}
    if evidence:
        updates["evidence"] = evidence
    t.update(**updates)
    console.print(f"[green]Task '{task_id}' marked as done.[/green]")


@task.command(name="note")
@click.argument("task_id")
@click.argument("note")
def task_note(task_id, note):
    """Append a timestamped note to a task's evidence log."""
    from datetime import datetime

    t = Task.get(task_id)
    if not t:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"[{timestamp}] {note}"
    existing = t.evidence or ""
    updated = (existing + "\n" + new_entry).strip()
    t.update(evidence=updated)
    console.print(f"[green]Note appended to '{task_id}'.[/green]")


@task.command(name="next")
def task_next() -> None:
    """Show the next highest-priority todo task, with phase-gap diagnosis."""
    p = get_current_project()
    t = Task.get_next(p.id)
    if t:
        console.print(f"[cyan]ID:[/cyan] {t.id}")
        console.print(f"[cyan]Title:[/cyan] {t.title}")
        console.print(f"[cyan]Status:[/cyan] {t.status}")
        console.print(f"[cyan]Priority:[/cyan] {t.priority}")
        console.print(f"[cyan]Phase:[/cyan] {t.phase or 'N/A'}")
        console.print(f"[cyan]Description:[/cyan] {t.description or 'N/A'}")
        console.print(f"[cyan]Acceptance Criteria:[/cyan]\n{t.acceptance or 'N/A'}")
        return

    counts = Task.count_by_status(p.id)
    total = sum(counts.values())

    if total == 0:
        console.print("[yellow]No tasks defined.[/yellow] The next phase has not been planned yet.")
        console.print("Action: Ask the user what the next phase of work should be, then run:")
        console.print(
            '  [cyan]engram task add "<task title>" --phase "Phase N" --priority high[/cyan]'
        )
    elif all(s in ("done", "cancelled") for s in counts):
        console.print("[green]All tasks complete.[/green] This phase is done.")
        console.print(
            "Action: Confirm with the user whether to plan the next phase or close the project."
        )
        console.print('  [cyan]engram task add "<next task>"[/cyan]  to continue')
    else:
        blocked = counts.get("blocked", 0)
        console.print(f"[red]All remaining tasks are blocked[/red] ({blocked} blocked).")
        console.print("Action: Resolve blockers before continuing. Review each blocked task:")
        console.print("  [cyan]engram task list --status blocked[/cyan]")


# --- Memory Commands ---


@cli.group()
def memory() -> None:
    """Manage memories (freeform notes and snippets)."""
    pass


def _type_add(
    memory_type: str, title: str, content: str, tags: str | None, always_include: bool
) -> None:
    """Shared implementation for type-specific add commands."""
    p = get_current_project()
    m = Memory.create(
        project_id=p.id,
        title=title,
        content=content,
        type=memory_type,
        tags=tags.split(",") if tags else [],
        always_include=always_include,
    )
    console.print(f"[green]{memory_type.capitalize()} recorded with ID:[/green] {m.id}")


def _type_list(memory_type: str) -> None:
    """Shared implementation for type-specific list commands."""
    p = get_current_project()
    memories = Memory.list_by_type(p.id, memory_type)
    if not memories:
        console.print(f"No {memory_type}s found. Add one with: engram {memory_type} add")
        return
    label = memory_type.capitalize() + "s"
    table = Table(
        title=f"{label} for Project: {p.name}", header_style="bold magenta", border_style="magenta"
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Tags", style="dim blue")
    table.add_column("Always Include", style="dim")
    for m in memories:
        table.add_row(m.id, m.title, ", ".join(m.tags), "yes" if m.always_include else "no")
    console.print(table)


def _type_search(memory_type: str, query: str) -> None:
    """Shared implementation for type-specific search commands."""
    results = Memory.search(query, type_filter=memory_type)
    if not results:
        console.print(f"No {memory_type}s found matching '{query}'.")
        return
    table = Table(
        title=f"{memory_type.capitalize()} Search: {query}",
        header_style="bold yellow",
        border_style="yellow",
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Snippet", style="dim")
    for m in results:
        snippet = (
            m.content[:70].replace("\n", " ") + "..."
            if len(m.content) > 70
            else m.content.replace("\n", " ")
        )
        table.add_row(m.id, m.title, snippet)
    console.print(table)


def _type_get(memory_id: str) -> None:
    """Shared implementation for type-specific get commands."""
    m = Memory.get(memory_id)
    if not m:
        console.print(f"[red]Error:[/red] Memory '{memory_id}' not found.")
        return
    console.print(f"[cyan]ID:[/cyan] {m.id}")
    console.print(f"[cyan]Title:[/cyan] {m.title}")
    console.print(f"[cyan]Type:[/cyan] {m.type}")
    console.print(f"[cyan]Tags:[/cyan] {', '.join(m.tags)}")
    console.print(f"[cyan]Always Include:[/cyan] {m.always_include}")
    console.print(f"[cyan]Content:[/cyan]\n{m.content}")


# --- Constraint Commands ---


@cli.group()
def constraint() -> None:
    """Constraints: hard rules agents must NEVER violate. Auto-surfaced at startup."""
    pass


@constraint.command(name="add")
@click.argument("title")
@click.option("--content", required=True, help="The rule and why it exists")
@click.option("--tags", help="Comma-separated tags")
@click.option(
    "--no-always-include", is_flag=True, default=False, help="Don't always include in context"
)
def constraint_add(title: str, content: str, tags: str | None, no_always_include: bool) -> None:
    """Record a hard constraint (always shown at startup by default)."""
    _type_add("constraint", title, content, tags, always_include=not no_always_include)


@constraint.command(name="list")
def constraint_list() -> None:
    """List all constraints for this project."""
    _type_list("constraint")


@constraint.command(name="search")
@click.argument("query")
def constraint_search(query: str) -> None:
    """Search constraints using full-text search."""
    _type_search("constraint", query)


@constraint.command(name="get")
@click.argument("memory_id")
def constraint_get(memory_id: str) -> None:
    """Show full constraint detail."""
    _type_get(memory_id)


# --- Lesson Commands ---


@cli.group()
def lesson() -> None:
    """Lessons: solved problems agents should not re-solve. Auto-surfaced at startup."""
    pass


@lesson.command(name="add")
@click.argument("title")
@click.option("--content", required=True, help="What the problem was and how it was solved")
@click.option("--tags", help="Comma-separated tags")
@click.option(
    "--no-always-include", is_flag=True, default=False, help="Don't always include in context"
)
def lesson_add(title: str, content: str, tags: str | None, no_always_include: bool) -> None:
    """Record a lesson learned (always shown at startup by default)."""
    _type_add("lesson", title, content, tags, always_include=not no_always_include)


@lesson.command(name="list")
def lesson_list() -> None:
    """List all lessons for this project."""
    _type_list("lesson")


@lesson.command(name="search")
@click.argument("query")
def lesson_search(query: str) -> None:
    """Search lessons using full-text search."""
    _type_search("lesson", query)


@lesson.command(name="get")
@click.argument("memory_id")
def lesson_get(memory_id: str) -> None:
    """Show full lesson detail."""
    _type_get(memory_id)


# --- Decision Commands ---


@cli.group()
def decision() -> None:
    """Decisions: architectural choices with rationale. Auto-surfaced at startup."""
    pass


@decision.command(name="add")
@click.argument("title")
@click.option("--content", required=True, help="What was decided and why")
@click.option("--tags", help="Comma-separated tags")
@click.option(
    "--no-always-include", is_flag=True, default=False, help="Don't always include in context"
)
def decision_add(title: str, content: str, tags: str | None, no_always_include: bool) -> None:
    """Record an architectural decision (always shown at startup by default)."""
    _type_add("decision", title, content, tags, always_include=not no_always_include)


@decision.command(name="list")
def decision_list() -> None:
    """List all decisions for this project."""
    _type_list("decision")


@decision.command(name="search")
@click.argument("query")
def decision_search(query: str) -> None:
    """Search decisions using full-text search."""
    _type_search("decision", query)


@decision.command(name="get")
@click.argument("memory_id")
def decision_get(memory_id: str) -> None:
    """Show full decision detail."""
    _type_get(memory_id)


# --- Snippet Commands ---


@cli.group()
def snippet() -> None:
    """Snippets: reusable commands, configs, and code patterns."""
    pass


@snippet.command(name="add")
@click.argument("title")
@click.option("--content", required=True, help="The reusable command or code")
@click.option("--tags", help="Comma-separated tags")
@click.option("--always-include", is_flag=True, default=False, help="Always include in context")
def snippet_add(title: str, content: str, tags: str | None, always_include: bool) -> None:
    """Record a reusable command or code snippet (search on demand)."""
    _type_add("snippet", title, content, tags, always_include=always_include)


@snippet.command(name="list")
def snippet_list() -> None:
    """List all snippets for this project."""
    _type_list("snippet")


@snippet.command(name="search")
@click.argument("query")
def snippet_search(query: str) -> None:
    """Search snippets using full-text search."""
    _type_search("snippet", query)


@snippet.command(name="get")
@click.argument("memory_id")
def snippet_get(memory_id: str) -> None:
    """Show full snippet detail."""
    _type_get(memory_id)


@memory.command(name="add")
@click.argument("title")
@click.option("--content", required=True, help="Memory content (required)")
@click.option(
    "--type",
    default="note",
    type=click.Choice(["note", "lesson", "decision", "constraint", "snippet"]),
    help="Memory type",
)
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
        always_include=always_include,
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

    table = Table(
        title=f"Memories for Project: {p.name}", header_style="bold blue", border_style="blue"
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Type", style="magenta")
    table.add_column("Tags", style="dim blue")

    for m in memories:
        table.add_row(m.id, m.title, m.type, ", ".join(m.tags))

    console.print(table)


@memory.command(name="search")
@click.argument("query")
@click.option("--type", help="Filter by memory type")
@click.option("--tag", "tags", multiple=True, help="Filter by tag (can be used multiple times)")
def memory_search(query, type, tags):
    """Search memories using FTS5."""
    results = Memory.search(query, type_filter=type, tag_filters=tags)
    if not results:
        console.print("No results found.")
        return

    table = Table(
        title=f"Search Results for: {query}", header_style="bold yellow", border_style="yellow"
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Snippet", style="dim")

    for m in results:
        # Simple snippet
        snippet = (
            m.content[:70].replace("\n", " ") + "..."
            if len(m.content) > 70
            else m.content.replace("\n", " ")
        )
        table.add_row(m.id, m.title, snippet)

    console.print(table)


@memory.command(name="get")
@click.argument("memory_id")
def memory_get(memory_id):
    """Show memory details."""
    m = Memory.get(memory_id)
    if not m:
        console.print(f"[red]Error:[/red] Memory '{memory_id}' not found.")
        return

    console.print(f"[cyan]ID:[/cyan] {m.id}")
    console.print(f"[cyan]Title:[/cyan] {m.title}")
    console.print(f"[cyan]Type:[/cyan] {m.type}")
    console.print(f"[cyan]Tags:[/cyan] {', '.join(m.tags)}")
    console.print(f"[cyan]Always Include:[/cyan] {m.always_include}")
    console.print(f"[cyan]Content:[/cyan]\n{m.content}")


VALID_MEMORY_FIELDS = {"title", "content", "type", "tags", "always_include"}
VALID_MEMORY_TYPES = {"note", "lesson", "decision", "constraint", "snippet"}


@memory.command(name="update")
@click.argument("memory_id")
@click.option("--field", help="Field to update (title, content, type, tags, always_include)")
@click.option("--value", help="New value for the field")
def memory_update(memory_id, field, value):
    """Update a memory field."""
    m = Memory.get(memory_id)
    if not m:
        console.print(f"[red]Error:[/red] Memory '{memory_id}' not found.")
        return

    if not field or value is None:
        console.print("[yellow]Please provide both --field and --value.[/yellow]")
        return

    if field not in VALID_MEMORY_FIELDS:
        console.print(
            f"[red]Error:[/red] Unknown field '{field}'. Valid fields: {', '.join(sorted(VALID_MEMORY_FIELDS))}"
        )
        return

    if field == "type" and value not in VALID_MEMORY_TYPES:
        console.print(
            f"[red]Error:[/red] Invalid type '{value}'. Valid: {', '.join(sorted(VALID_MEMORY_TYPES))}"
        )
        return

    if field == "tags":
        value = value.split(",")
    elif field == "always_include":
        value = value.lower() in ("true", "1", "yes")

    m.update(**{field: value})
    console.print(f"[green]Memory '{memory_id}' updated.[/green]")


@memory.command(name="delete")
@click.argument("memory_id")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
def memory_delete(memory_id, yes):
    """Delete a memory."""
    m = Memory.get(memory_id)
    if not m:
        console.print(f"[red]Error:[/red] Memory '{memory_id}' not found.")
        return

    if yes or click.confirm(f"Are you sure you want to delete memory '{memory_id}'?"):
        m.delete()
        console.print(f"[green]Memory '{memory_id}' deleted.[/green]")


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
        console.print(
            f"[yellow]An active session already exists:[/yellow] {active.id} (Goal: {active.goal})"
        )
        if click.confirm("Close it and start a new one?"):
            active.close(summary="Automatically closed to start new session.")
        else:
            return

    s = Session.create(project_id=p.id, goal=goal)
    console.print(f"[green]Session started with ID:[/green] {s.id}")


@session.command(name="close")
@click.option("--summary", required=True, help="What did you accomplish? (required)")
@click.option("--next-steps", help="What are the next steps?")
def session_close(summary, next_steps):
    """Close the active work session. If none exists, auto-creates one."""
    p = get_current_project()
    s = Session.get_active(p.id)
    if not s:
        # Auto-create a session so session close is always safe to call
        s = Session.create(project_id=p.id, goal="(auto)")

    s.close(summary=summary, next_steps=next_steps)
    console.print(f"[green]Session '{s.id}' closed.[/green]")


@session.command(name="list")
@click.option("--active", is_flag=True, help="Show only active (open) sessions")
def session_list(active):
    """List sessions for the current project (all by default)."""
    p = get_current_project()
    sessions = Session.list_by_project(p.id)

    if active:
        sessions = [s for s in sessions if s.status == "open"]

    if not sessions:
        console.print("No sessions found.")
        return

    table = Table(
        title=f"Sessions for Project: {p.name}", header_style="bold yellow", border_style="yellow"
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold green")
    table.add_column("Goal", style="white")
    table.add_column("Started At", style="dim yellow")

    for s in sessions:
        status_style = "green" if s.status == "open" else "dim blue"
        table.add_row(
            s.id, f"[{status_style}]{s.status}[/{status_style}]", s.goal or "N/A", s.started_at
        )

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


# --- Export Commands ---


@cli.group()
def export():
    """Export project data."""
    pass


@export.command(name="snapshot")
@click.option("--output", "-o", help="Output file path (default: SNAPSHOT.md)")
def export_snapshot(output):
    """Export a full project snapshot to Markdown."""
    p = get_current_project()
    ctx = get_snapshot_context(p.id)

    filename = output or "SNAPSHOT.md"
    with open(filename, "w") as f:
        f.write(ctx)

    console.print(f"[green]Snapshot exported to:[/green] {filename}")


@export.command(name="handoff")
@click.option("--output", "-o", help="Output file path (default: HANDOFF.md)")
def export_handoff(output):
    """Export a project handoff for another agent."""
    p = get_current_project()
    ctx = get_handoff_context(p.id)

    filename = output or "HANDOFF.md"
    with open(filename, "w") as f:
        f.write(ctx)

    console.print(f"[green]Handoff exported to:[/green] {filename}")


# --- Commit Command ---

CONVENTIONAL_COMMIT_TYPES = {
    "feat",
    "fix",
    "docs",
    "chore",
    "refactor",
    "test",
    "ci",
    "style",
    "perf",
}


@cli.command(name="commit")
@click.option("-m", "--message", required=True, help="Commit message (Conventional Commits format)")
@click.option(
    "--no-validate", is_flag=True, default=False, help="Skip commit message format validation"
)
def commit(message: str, no_validate: bool) -> None:
    """Atomic commit: stage all, validate message, commit (pre-commit hooks run automatically)."""
    import re
    import subprocess

    if not no_validate:
        pattern = rf"^({'|'.join(CONVENTIONAL_COMMIT_TYPES)})(\(.+\))?: .+"
        if not re.match(pattern, message):
            console.print(
                "[red]Error:[/red] Commit message does not follow Conventional Commits format."
            )
            console.print("  Expected: [cyan]type(scope): description[/cyan]")
            console.print(f"  Types: {', '.join(sorted(CONVENTIONAL_COMMIT_TYPES))}")
            console.print("  Example: [cyan]feat(cli): add lesson command [T-001][/cyan]")
            return
        if "[" not in message:
            console.print(
                "[yellow]Warning:[/yellow] No task ID found in message. Recommended: add [task-id]"
            )

    console.print("[dim]Staging all changes...[/dim]")
    result = subprocess.run(["git", "add", "-A"], capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[red]git add failed:[/red] {result.stderr.strip()}")
        return

    console.print("[dim]Committing... (pre-commit hooks will run if installed)[/dim]")
    result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
    if result.returncode != 0:
        console.print(
            f"[red]Commit failed:[/red]\n{result.stdout.strip()}\n{result.stderr.strip()}"
        )
        return

    # Extract and display the short commit hash
    hash_result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
    )
    commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else "unknown"
    console.print(f"[green]Committed:[/green] {commit_hash}  {message}")


@cli.command(name="guide")
@click.argument("section", required=False)
def guide(section):
    """Show the User Manual. Optional: provide a section (concepts, commands, workflow, troubleshooting)."""
    import re
    from importlib import resources

    from rich.markdown import Markdown

    try:
        # Load from the installed package resource — works regardless of cwd
        pkg = resources.files("engram")
        content = (pkg / "USER_MANUAL.md").read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[red]Error reading manual:[/red] {str(e)}")
        return

    if section:
        section = section.lower()
        mapping = {
            "concepts": "## 1. Core Concepts",
            "commands": "## 2. Command Reference",
            "workflow": "## 3. Recommended Agent Workflow",
            "troubleshooting": "## 4. Troubleshooting",
        }

        header = mapping.get(section)
        if header:
            parts = re.split(r"(\n##\s.*?\n|\n---)", content)
            found = False
            section_content = ""
            for i in range(len(parts)):
                if header in parts[i]:
                    found = True
                    section_content = parts[i] + (parts[i + 1] if i + 1 < len(parts) else "")
                    break

            if found:
                content = f"# Engram Guide: {section.capitalize()}\n\n" + section_content
            else:
                console.print(f"[yellow]Section '{section}' not found.[/yellow]")
                return

    console.print(Markdown(content))


def main():
    cli()


if __name__ == "__main__":
    main()
