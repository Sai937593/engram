"""Lifecycle task commands: add, start, done, and next."""

import uuid

import click

import engram.cli as cli_root
from engram.cli.phase_helpers import resolve_phase_for_task_add
from engram.cli.task_cmds import task
from engram.cli.task_helpers import (
    blocked_dependency_messages,
    check_dependency_cycle,
    get_effective_status,
    resolve_task_dependency,
)
from engram.cli.task_rendering import (
    print_all_tasks_complete_message_for_next,
    print_next_task_details,
    print_no_tasks_defined_message,
    status_counts,
)
from engram.models.task import Task


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
    project = cli_root.get_current_project()
    resolved_dep = None
    resolved_phase = phase
    resolved_phase_id = None
    task_id = uuid.uuid4().hex[:8]
    if depends_on:
        resolved_dep = resolve_task_dependency(depends_on, project.id)
        check_dependency_cycle(task_id, resolved_dep, project.id)
    if phase is not None:
        resolved_phase, resolved_phase_id = resolve_phase_for_task_add(phase, project.id)

    created_task = Task.create(
        project_id=project.id,
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
    cli_root.console.print(f"[green]Task created with ID:[/green] {created_task.id}")


@task.command(name="start")
@click.argument("task_id")
def task_start(task_id: str) -> None:
    """Mark a task as in-progress (claim it)."""
    task_item = Task.get(task_id)
    if not task_item:
        cli_root.console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return

    effective_status = get_effective_status(task_item)
    if effective_status == "blocked":
        blockers = blocked_dependency_messages(task_item, include_status=True)
        cli_root.console.print(
            f"[red]Error:[/red] Task '{task_id}' is blocked by unfinished dependency/dependencies: {', '.join(blockers)}"
        )
        return

    if effective_status == "cancelled":
        cli_root.console.print(
            f"[red]Error:[/red] Task '{task_id}' is cancelled (either directly or by a cancelled dependency)."
        )
        return

    if task_item.status == "in-progress":
        cli_root.console.print(f"[yellow]Task '{task_id}' is already in-progress.[/yellow]")
        return

    task_item.update(status="in-progress")
    cli_root.console.print(f"[green]Task '{task_id}' marked as in-progress.[/green]")


@task.command(name="done")
@click.argument("task_id")
@click.option("--evidence", help="Evidence of completion (tests, PR, etc.)")
def task_done(task_id: str, evidence: str | None) -> None:
    """Mark a task as done (optionally record evidence)."""
    task_item = Task.get(task_id)
    if not task_item:
        cli_root.console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return

    effective_status = get_effective_status(task_item)
    if effective_status == "blocked" and task_item.status != "done":
        blockers = blocked_dependency_messages(task_item, include_status=False)
        cli_root.console.print(
            f"[red]Error:[/red] Cannot mark '{task_id}' as done. It is blocked by unfinished dependency/dependencies: {', '.join(blockers)}"
        )
        return

    updates = {"status": "done"}
    if evidence:
        updates["evidence"] = evidence
    task_item.update(**updates)
    cli_root.console.print(f"[green]Task '{task_id}' marked as done.[/green]")


@task.command(name="next")
def task_next() -> None:
    """Show the next highest-priority todo task, with phase-gap diagnosis."""
    project = cli_root.get_current_project()
    task_item = Task.get_next(project.id)
    if task_item:
        print_next_task_details(task_item)
        return

    tasks = Task.list_by_project(project.id)
    counts = status_counts(tasks)

    total = sum(counts.values())
    if total == 0:
        print_no_tasks_defined_message()
    elif all(status in ("done", "cancelled") for status in counts):
        print_all_tasks_complete_message_for_next()
    else:
        blocked = counts.get("blocked", 0)
        cli_root.console.print(f"[red]All remaining tasks are blocked[/red] ({blocked} blocked).")
        cli_root.console.print(
            "Action: Resolve blockers before continuing. Review each blocked task:"
        )
        cli_root.console.print("  [cyan]engram task list --status blocked[/cyan]")
