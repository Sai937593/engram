"""Task management commands."""

import uuid
from datetime import datetime

import click
from rich.table import Table

import engram.cli as cli_root
from engram.cli.phase_helpers import (
    normalize_phase_title,
    resolve_phase_for_task_add,
    resolve_phase_in_project,
)
from engram.db import get_db_connection
from engram.models.task import Task, get_effective_phase_title

VALID_TASK_FIELDS = {
    "title",
    "status",
    "priority",
    "description",
    "tags",
    "acceptance",
    "phase",
    "phase_id",
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


def check_dependency_cycle(task_id: str, depends_on_id: str | None, project_id: str) -> None:
    """Check if adding depends_on_id as a dependency of task_id would create a cycle.

    Raises:
        click.ClickException: If a circular dependency is detected.
    """
    if not depends_on_id:
        return

    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, depends_on FROM tasks WHERE project_id = ?", (project_id,)
    ).fetchall()
    conn.close()

    dep_map = {row["id"]: row["depends_on"] for row in rows}
    dep_map[task_id] = depends_on_id

    visited = set()
    path = set()

    def dfs(node: str) -> bool:
        if node in path:
            return True
        if node in visited:
            return False

        path.add(node)
        dep = dep_map.get(node)
        if dep:
            if dfs(dep):
                return True
        path.remove(node)
        visited.add(node)
        return False

    if dfs(task_id):
        raise click.ClickException("Circular dependency detected.")


def get_effective_status(task: Task) -> str:
    """Calculate the implicit/effective status of the task based on dependencies."""
    if task.status in ("done", "cancelled"):
        return task.status

    visited = set()
    curr = task
    has_unfinished = False
    has_blocked = False
    has_cancelled = False

    while curr.depends_on:
        if curr.depends_on in visited:
            break
        visited.add(curr.depends_on)
        dep = Task.get(curr.depends_on)
        if not dep:
            break
        if dep.status == "cancelled":
            has_cancelled = True
            break  # cancelled is a terminal state that propagates fully
        elif dep.status == "blocked":
            has_blocked = True
        elif dep.status != "done":
            has_unfinished = True
        curr = dep

    if has_cancelled:
        return "cancelled"
    if has_blocked or has_unfinished:
        return "blocked"

    return task.status


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
    resolved_phase = phase
    resolved_phase_id = None
    task_id = uuid.uuid4().hex[:8]
    if depends_on:
        resolved_dep = resolve_task_dependency(depends_on, p.id)
        check_dependency_cycle(task_id, resolved_dep, p.id)
    if phase is not None:
        resolved_phase, resolved_phase_id = resolve_phase_for_task_add(phase, p.id)

    t = Task.create(
        project_id=p.id,
        title=title,
        description=description,
        priority=priority,
        status=status,
        tags=tags.split(",") if tags else [],
        acceptance=acceptance,
        phase=resolved_phase,
        phase_id=resolved_phase_id,
        depends_on=resolved_dep,
        id=task_id,
    )
    cli_root.console.print(f"[green]Task created with ID:[/green] {t.id}")


@task.command(name="start")
@click.argument("task_id")
def task_start(task_id: str) -> None:
    """Mark a task as in-progress (claim it)."""
    t = Task.get(task_id)
    if not t:
        cli_root.console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return

    eff_status = get_effective_status(t)
    if eff_status == "blocked":
        visited = set()
        curr = t
        blockers = []
        while curr.depends_on:
            if curr.depends_on in visited:
                break
            visited.add(curr.depends_on)
            dep = Task.get(curr.depends_on)
            if not dep:
                break
            if dep.status != "done":
                blockers.append(f"'{dep.id}' ({dep.title}, status: {dep.status})")
            curr = dep
        cli_root.console.print(
            f"[red]Error:[/red] Task '{task_id}' is blocked by unfinished dependency/dependencies: {', '.join(blockers)}"
        )
        return

    if eff_status == "cancelled":
        cli_root.console.print(
            f"[red]Error:[/red] Task '{task_id}' is cancelled (either directly or by a cancelled dependency)."
        )
        return

    if t.status == "in-progress":
        cli_root.console.print(f"[yellow]Task '{task_id}' is already in-progress.[/yellow]")
        return

    t.update(status="in-progress")
    cli_root.console.print(f"[green]Task '{task_id}' marked as in-progress.[/green]")


@task.command(name="list")
@click.option(
    "--status",
    default="todo",
    help="Filter by status (default: todo, use 'all' to show all tasks)",
)
@click.option(
    "--all",
    "-a",
    "show_all",
    is_flag=True,
    help="Show all tasks regardless of status (equivalent to --status all)",
)
@click.option("--phase", help="Filter tasks to a phase ID or unique phase title")
def task_list(status: str, show_all: bool, phase: str | None) -> None:
    """List tasks for the current project."""
    p = cli_root.get_current_project()
    tasks = Task.list_by_project(p.id)
    if phase is not None:
        resolved_phase = resolve_phase_in_project(phase, p.id)
        resolved_phase_title = normalize_phase_title(resolved_phase.title)
        tasks = [
            task
            for task in tasks
            if (
                (task.phase_id == resolved_phase.id)
                if task.phase_id
                else normalize_phase_title(task.phase) == resolved_phase_title
            )
        ]
    if show_all:
        status = "all"
    if status.lower() != "all":
        tasks = [t for t in tasks if get_effective_status(t) == status.lower()]
    if not tasks:
        # Check if the project has absolutely no tasks
        all_tasks = Task.list_by_project(p.id)
        if not all_tasks:
            cli_root.console.print(
                "[yellow]No tasks defined.[/yellow] The next phase has not been planned yet."
            )
            cli_root.console.print(
                "Action: Ask the user what the next phase of work should be, then run:"
            )
            cli_root.console.print(
                '  [cyan]engram task add "<task title>" --phase "Phase N" --priority high[/cyan]'
            )
        else:
            # Count tasks by their effective status to reflect implicit blockers
            counts = {}
            for t in all_tasks:
                eff_status = get_effective_status(t)
                counts[eff_status] = counts.get(eff_status, 0) + 1

            if status.lower() == "todo" and all(s in ("done", "cancelled") for s in counts):
                cli_root.console.print("[green]All tasks complete.[/green] This phase is done.")
                cli_root.console.print(
                    "Action: Confirm with the user whether to plan the next phase or close the project."
                )
                cli_root.console.print('  [cyan]engram task add "<next task>"[/cyan] to continue')
            else:
                cli_root.console.print(f"No tasks found with status '{status}'.")
        return

    table = Table(
        title=f"Tasks for Project: {p.name}", header_style="bold green", border_style="green"
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Phase", style="blue")
    table.add_column("Status", style="bold green")
    table.add_column("Priority", style="yellow")
    table.add_column("Depends On", style="magenta")

    for t in tasks:
        eff_status = get_effective_status(t)
        status_style = "green"
        if eff_status == "blocked":
            status_style = "red"
        elif eff_status == "done":
            status_style = "blue"
        elif eff_status == "in-progress":
            status_style = "yellow"
        elif eff_status == "cancelled":
            status_style = "dim white"

        status_str = eff_status
        if eff_status != t.status:
            status_str = f"{eff_status} (dep)"

        priority_style = "bold red" if t.priority == "high" else "yellow"
        table.add_row(
            t.id,
            t.title,
            get_effective_phase_title(t) or "-",
            f"[{status_style}]{status_str}[/{status_style}]",
            f"[{priority_style}]{t.priority}[/{priority_style}]",
            t.depends_on or "-",
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
        check_dependency_cycle(task_id, resolved_dep, t.project_id)
        value = resolved_dep
    elif field == "phase_id":
        if value.lower() in ("none", "null", "clear"):
            t.update(phase_id=None, phase=None)
            cli_root.console.print(f"[green]Task '{task_id}' updated.[/green]")
            return
        else:
            resolved_phase = resolve_phase_in_project(value, t.project_id)
            t.update(phase_id=resolved_phase.id, phase=resolved_phase.title)
            cli_root.console.print(f"[green]Task '{task_id}' updated.[/green]")
            return

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

    eff_status = get_effective_status(t)
    status_str = eff_status
    if eff_status != t.status:
        status_str = f"{eff_status} (propagated from dependency)"
    cli_root.console.print(f"[cyan]Status:[/cyan] {status_str}")
    cli_root.console.print(f"[cyan]Priority:[/cyan] {t.priority}")
    cli_root.console.print(f"[cyan]Depends On:[/cyan] {t.depends_on or 'N/A'}")
    cli_root.console.print(f"[cyan]Phase:[/cyan] {get_effective_phase_title(t) or 'N/A'}")
    cli_root.console.print(f"[cyan]Description:[/cyan] {t.description or 'N/A'}")
    cli_root.console.print(f"[cyan]Acceptance Criteria:[/cyan]\n{t.acceptance or 'N/A'}")
    cli_root.console.print(f"[cyan]Evidence / Notes:[/cyan]\n{t.evidence or 'N/A'}")
    cli_root.console.print(f"[cyan]Tags:[/cyan] {', '.join(t.tags)}")


@task.command(name="done")
@click.argument("task_id")
@click.option("--evidence", help="Evidence of completion (tests, PR, etc.)")
def task_done(task_id: str, evidence: str | None) -> None:
    """Mark a task as done (optionally record evidence)."""
    t = Task.get(task_id)
    if not t:
        cli_root.console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return

    eff_status = get_effective_status(t)
    if eff_status == "blocked" and t.status != "done":
        visited = set()
        curr = t
        blockers = []
        while curr.depends_on:
            if curr.depends_on in visited:
                break
            visited.add(curr.depends_on)
            dep = Task.get(curr.depends_on)
            if not dep:
                break
            if dep.status != "done":
                blockers.append(f"'{dep.id}' ({dep.title})")
            curr = dep
        cli_root.console.print(
            f"[red]Error:[/red] Cannot mark '{task_id}' as done. It is blocked by unfinished dependency/dependencies: {', '.join(blockers)}"
        )
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

        eff_status = get_effective_status(t)
        status_str = eff_status
        if eff_status != t.status:
            status_str = f"{eff_status} (dep)"
        cli_root.console.print(f"[cyan]Status:[/cyan] {status_str}")
        cli_root.console.print(f"[cyan]Priority:[/cyan] {t.priority}")
        cli_root.console.print(f"[cyan]Phase:[/cyan] {t.phase or 'N/A'}")
        cli_root.console.print(f"[cyan]Description:[/cyan] {t.description or 'N/A'}")
        cli_root.console.print(f"[cyan]Acceptance Criteria:[/cyan]\n{t.acceptance or 'N/A'}")
        return

    # Count tasks by their effective status to reflect implicit blockers
    tasks = Task.list_by_project(p.id)
    counts = {}
    for task in tasks:
        eff_status = get_effective_status(task)
        counts[eff_status] = counts.get(eff_status, 0) + 1

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
