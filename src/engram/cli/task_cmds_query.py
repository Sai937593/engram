"""Read/query task commands: list and get."""

import click

import engram.cli as cli_root
from engram.cli.phase_helpers import normalize_phase_title, resolve_phase_in_project
from engram.cli.task_cmds import task
from engram.cli.task_helpers import get_effective_status
from engram.cli.task_rendering import (
    print_all_tasks_complete_message,
    print_no_tasks_defined_message,
    print_task_details,
    render_task_table,
    status_counts,
)
from engram.models.task import Task


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
    project = cli_root.get_current_project()
    tasks = Task.list_by_project(project.id)
    if phase is not None:
        resolved_phase = resolve_phase_in_project(phase, project.id)
        resolved_phase_title = normalize_phase_title(resolved_phase.title)
        tasks = [
            task_item
            for task_item in tasks
            if (
                (task_item.phase_id == resolved_phase.id)
                if task_item.phase_id
                else normalize_phase_title(task_item.phase) == resolved_phase_title
            )
        ]
    if show_all:
        status = "all"
    if status.lower() != "all":
        tasks = [
            task_item for task_item in tasks if get_effective_status(task_item) == status.lower()
        ]

    if not tasks:
        all_tasks = Task.list_by_project(project.id)
        if not all_tasks:
            print_no_tasks_defined_message()
        else:
            counts = status_counts(all_tasks)
            if status.lower() == "todo" and all(s in ("done", "cancelled") for s in counts):
                print_all_tasks_complete_message()
            else:
                cli_root.console.print(f"No tasks found with status '{status}'.")
        return

    cli_root.console.print(render_task_table(project, tasks))


@task.command(name="get")
@click.argument("task_id")
def task_get(task_id: str) -> None:
    """Show task details."""
    task_item = Task.get(task_id)
    if not task_item:
        cli_root.console.print(f"[red]Error:[/red] Task '{task_id}' not found.")
        return

    print_task_details(task_item)
