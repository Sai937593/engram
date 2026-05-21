"""Task management commands."""

from datetime import datetime

import click
from rich.table import Table

import engram.cli as cli_root
from engram.db import get_db_connection
from engram.models.task import Task

VALID_TASK_FIELDS = {
    "title",
    "status",
    "priority",
    "description",
    "tags",
    "acceptance",
    "phase",
    "evidence",
    "depends_on",
}
VALID_TASK_STATUSES = {"todo", "in-progress", "done", "blocked", "cancelled"}
VALID_TASK_PRIORITIES = {"low", "medium", "high", "critical"}


def resolve_task_dependency(value: str | None, project_id: str) -> str | None:
    """Resolve a partial or exact task ID to a full 8-character ID."""
    if not value or value.lower() in ("none", "null", "clear"):
        return None

    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id FROM tasks WHERE project_id = ? AND (id = ? OR id LIKE ?)",
        (project_id, value, value + "%"),
    ).fetchall()
    conn.close()

    matching_ids = sorted(list(set(row["id"] for row in rows)))

    if not matching_ids:
        raise click.ClickException(f"Task dependency '{value}' not found in this project.")

    if len(matching_ids) > 1:
        if value in matching_ids:
            return value
        raise click.ClickException(
            f"Ambiguous task dependency '{value}'. Multiple matches found: {', '.join(matching_ids)}"
        )

    return matching_ids[0]


@cli_root.cli.group()
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
@click.option("--depends-on", "-d", help="Task ID or 8-char prefix that this task depends on")
def task_add(
    title: str,
    description: str | None,
    priority: str,
    status: str,
    tags: str | None,
    acceptance: str | None,
    phase: str | None,
    depends_on: str | None = None,
) -> None:
    """Add a new task to the current project."""
    p = cli_root.get_current_project()
    resolved_dep = None
    if depends_on:
        resolved_dep = resolve_task_dependency(depends_on, p.id)

    t = Task.create(
        project_id=p.id,
        title=title,
        description=description,
        priority=priority,
        status=status,
        tags=tags.split(",") if tags else [],
        acceptance=acceptance,
        phase=phase,
        depends_on=resolved_dep,
    )
    cli_root.console.print(f"[green]Task created with ID:[/green] {t.id}")


@task.command(name="start")
@click.argument("task_id")
def task_start(task_id):
    """Mark a task as in-progress (claim it)."""
    t = Task.get(task_id)
    if not t:
        cli_root.console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return
    if t.status == "in-progress":
        cli_root.console.print(f"[yellow]Task '{task_id}' is already in-progress.[/yellow]")
        return
    t.update(status="in-progress")
    cli_root.console.print(f"[green]Task '{task_id}' marked as in-progress.[/green]")


@task.command(name="list")
@click.option("--status", help="Filter by status")
def task_list(status):
    """List tasks for the current project."""
    p = cli_root.get_current_project()
    tasks = Task.list_by_project(p.id)
    if status:
        tasks = [t for t in tasks if t.status == status]
    if not tasks:
        cli_root.console.print("No tasks found.")
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
        priority_style = "bold red" if t.priority == "high" else "yellow"
        table.add_row(
            t.id,
            t.title,
            f"[{status_style}]{t.status}[/{status_style}]",
            f"[{priority_style}]{t.priority}[/{priority_style}]",
        )
    cli_root.console.print(table)


@task.command(name="update")
@click.argument("task_id")
@click.option("--field", help="Field to update")
@click.option("--value", help="New value for the field")
def task_update(task_id: str, field: str, value: str) -> None:
    """Update a task field."""
    t = Task.get(task_id)
    if not t:
        cli_root.console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return
    if not field or not value:
        cli_root.console.print("[yellow]Please provide both --field and --value.[/yellow]")
        return
    if field not in VALID_TASK_FIELDS:
        cli_root.console.print(
            f"[red]Error:[/red] Unknown field '{field}'. Valid fields: {', '.join(sorted(VALID_TASK_FIELDS))}"
        )
        return
    if field == "status" and value not in VALID_TASK_STATUSES:
        cli_root.console.print(
            f"[red]Error:[/red] Invalid status '{value}'. Valid: {', '.join(sorted(VALID_TASK_STATUSES))}"
        )
        return
    if field == "priority" and value not in VALID_TASK_PRIORITIES:
        cli_root.console.print(
            f"[red]Error:[/red] Invalid priority '{value}'. Valid: {', '.join(sorted(VALID_TASK_PRIORITIES))}"
        )
        return

    terminal_statuses = {"done", "cancelled"}
    if field == "status" and t.status in terminal_statuses and value not in terminal_statuses:
        cli_root.console.print(
            f"[yellow]Warning: transitioning '{task_id}' from '{t.status}' to '{value}'. Continuing...[/yellow]"
        )

    if field == "tags":
        value = value.split(",")
    elif field == "depends_on":
        resolved_dep = resolve_task_dependency(value, t.project_id)
        if resolved_dep == task_id:
            raise click.ClickException("A task cannot depend on itself.")
        value = resolved_dep

    t.update(**{field: value})
    cli_root.console.print(f"[green]Task '{task_id}' updated.[/green]")


@task.command(name="get")
@click.argument("task_id")
def task_get(task_id: str) -> None:
    """Show task details."""
    t = Task.get(task_id)
    if not t:
        cli_root.console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return
    cli_root.console.print(f"[cyan]ID:[/cyan] {t.id}")
    cli_root.console.print(f"[cyan]Title:[/cyan] {t.title}")
    cli_root.console.print(f"[cyan]Status:[/cyan] {t.status}")
    cli_root.console.print(f"[cyan]Priority:[/cyan] {t.priority}")
    cli_root.console.print(f"[cyan]Depends On:[/cyan] {t.depends_on or 'N/A'}")
    cli_root.console.print(f"[cyan]Phase:[/cyan] {t.phase or 'N/A'}")
    cli_root.console.print(f"[cyan]Description:[/cyan] {t.description or 'N/A'}")
    cli_root.console.print(f"[cyan]Acceptance Criteria:[/cyan]\n{t.acceptance or 'N/A'}")
    cli_root.console.print(f"[cyan]Evidence / Notes:[/cyan]\n{t.evidence or 'N/A'}")
    cli_root.console.print(f"[cyan]Tags:[/cyan] {', '.join(t.tags)}")


@task.command(name="done")
@click.argument("task_id")
@click.option("--evidence", help="Evidence of completion (tests, PR, etc.)")
def task_done(task_id, evidence):
    """Mark a task as done (optionally record evidence)."""
    t = Task.get(task_id)
    if not t:
        cli_root.console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return

    updates = {"status": "done"}
    if evidence:
        updates["evidence"] = evidence
    t.update(**updates)
    cli_root.console.print(f"[green]Task '{task_id}' marked as done.[/green]")


@task.command(name="note")
@click.argument("task_id")
@click.argument("note")
def task_note(task_id, note):
    """Append a timestamped note to a task's evidence log."""
    t = Task.get(task_id)
    if not t:
        cli_root.console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"[{timestamp}] {note}"
    existing = t.evidence or ""
    updated = (existing + "\n" + new_entry).strip()
    t.update(evidence=updated)
    cli_root.console.print(f"[green]Note appended to '{task_id}'.[/green]")


@task.command(name="next")
def task_next() -> None:
    """Show the next highest-priority todo task, with phase-gap diagnosis."""
    p = cli_root.get_current_project()
    t = Task.get_next(p.id)
    if t:
        cli_root.console.print(f"[cyan]ID:[/cyan] {t.id}")
        cli_root.console.print(f"[cyan]Title:[/cyan] {t.title}")
        cli_root.console.print(f"[cyan]Status:[/cyan] {t.status}")
        cli_root.console.print(f"[cyan]Priority:[/cyan] {t.priority}")
        cli_root.console.print(f"[cyan]Phase:[/cyan] {t.phase or 'N/A'}")
        cli_root.console.print(f"[cyan]Description:[/cyan] {t.description or 'N/A'}")
        cli_root.console.print(f"[cyan]Acceptance Criteria:[/cyan]\n{t.acceptance or 'N/A'}")
        return

    counts = Task.count_by_status(p.id)
    total = sum(counts.values())
    if total == 0:
        cli_root.console.print(
            "[yellow]No tasks defined.[/yellow] The next phase has not been planned yet."
        )
        cli_root.console.print(
            "Action: Ask the user what the next phase of work should be, then run:"
        )
        cli_root.console.print(
            '  [cyan]engram task add "<task title>" --phase "Phase N" --priority high[/cyan]'
        )
    elif all(s in ("done", "cancelled") for s in counts):
        cli_root.console.print("[green]All tasks complete.[/green] This phase is done.")
        cli_root.console.print(
            "Action: Confirm with the user whether to plan the next phase or close the project."
        )
        cli_root.console.print('  [cyan]engram task add "<next task>"[/cyan]  to continue')
    else:
        blocked = counts.get("blocked", 0)
        cli_root.console.print(f"[red]All remaining tasks are blocked[/red] ({blocked} blocked).")
        cli_root.console.print(
            "Action: Resolve blockers before continuing. Review each blocked task:"
        )
        cli_root.console.print("  [cyan]engram task list --status blocked[/cyan]")
