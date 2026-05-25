"""Mutation task commands: update and note."""

from datetime import datetime

import click

import engram.cli as cli_root
from engram.cli.phase_helpers import resolve_phase_in_project
from engram.cli.task_cmds import task
from engram.cli.task_helpers import (
    VALID_TASK_FIELDS,
    VALID_TASK_PRIORITIES,
    VALID_TASK_STATUSES,
    check_dependency_cycle,
    resolve_task_dependency,
)
from engram.models.task import Task


@task.command(name="update")
@click.argument("task_id")
@click.option("--field", help="Field to update")
@click.option("--value", help="New value for the field")
def task_update(task_id: str, field: str, value: str) -> None:
    """Update a task field."""
    task_item = Task.get(task_id)
    if not task_item:
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
    if (
        field == "status"
        and task_item.status in terminal_statuses
        and value not in terminal_statuses
    ):
        cli_root.console.print(
            f"[yellow]Warning: transitioning '{task_id}' from '{task_item.status}' to '{value}'. Continuing...[/yellow]"
        )

    if field == "tags":
        value = value.split(",")
    elif field == "depends_on":
        resolved_dep = resolve_task_dependency(value, task_item.project_id)
        if resolved_dep == task_id:
            raise click.ClickException("A task cannot depend on itself.")
        check_dependency_cycle(task_id, resolved_dep, task_item.project_id)
        value = resolved_dep
    elif field == "phase_id":
        if value.lower() in ("none", "null", "clear"):
            task_item.update(phase_id=None, phase=None)
            cli_root.console.print(f"[green]Task '{task_id}' updated.[/green]")
            return

        resolved_phase = resolve_phase_in_project(value, task_item.project_id)
        task_item.update(phase_id=resolved_phase.id, phase=resolved_phase.title)
        cli_root.console.print(f"[green]Task '{task_id}' updated.[/green]")
        return
    elif field == "phase" and task_item.phase_id:
        raise click.ClickException(
            "Task is linked to a first-class phase. Use --field phase_id to change the "
            "effective phase, or --field phase_id --value none to clear the link first."
        )

    task_item.update(**{field: value})
    cli_root.console.print(f"[green]Task '{task_id}' updated.[/green]")


@task.command(name="note")
@click.argument("task_id")
@click.argument("note")
def task_note(task_id: str, note: str) -> None:
    """Append a timestamped note to a task's evidence log."""
    task_item = Task.get(task_id)
    if not task_item:
        cli_root.console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"[{timestamp}] {note}"
    existing = task_item.evidence or ""
    updated = (existing + "\n" + new_entry).strip()
    task_item.update(evidence=updated)
    cli_root.console.print(f"[green]Note appended to '{task_id}'.[/green]")
