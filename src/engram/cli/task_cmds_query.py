"""Read/query task commands: list and get."""

import click

import engram.cli as cli_root
from engram.cli.phase_helpers import normalize_phase_title, resolve_phase_in_project
from engram.cli.task_cmds import task
from engram.cli.task_helpers import (
    get_effective_status,
    parse_relevant_files_csv,
    resolve_task_id_in_project,
)
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


@task.group(name="files")
def task_files() -> None:
    """Manage relevant file path hints on tasks."""
    pass


def _resolve_task_for_files(task_id: str) -> Task:
    """Resolve a task for `task files` commands within the current project."""
    project = cli_root.get_current_project()
    resolved_task_id = resolve_task_id_in_project(task_id, project.id)
    task_item = Task.get(resolved_task_id)
    if task_item is None:
        raise click.ClickException(f"Task '{task_id}' not found in this project.")
    return task_item


@task_files.command(name="list")
@click.argument("task_id")
def task_files_list(task_id: str) -> None:
    """List relevant file paths for a task."""
    task_item = _resolve_task_for_files(task_id)
    if not task_item.relevant_files:
        cli_root.console.print(f"No relevant file paths set for task '{task_item.id}'.")
        return

    cli_root.console.print(f"Relevant file paths for task '{task_item.id}':")
    for path in task_item.relevant_files:
        cli_root.console.print(f"- {path}")


@task_files.command(name="add")
@click.argument("task_id")
@click.option("--files", required=True, help="Comma-separated relevant file paths to add")
def task_files_add(task_id: str, files: str) -> None:
    """Add relevant file paths to a task."""
    task_item = _resolve_task_for_files(task_id)
    new_paths = parse_relevant_files_csv(files)
    existing_paths = set(task_item.relevant_files)
    duplicates = [path for path in new_paths if path in existing_paths]
    if duplicates:
        raise click.ClickException(
            f"Task '{task_item.id}' already includes path(s): {', '.join(duplicates)}"
        )

    task_item.update(relevant_files=task_item.relevant_files + new_paths)
    cli_root.console.print(
        f"[green]Added {len(new_paths)} relevant file path(s) to task '{task_item.id}'.[/green]"
    )


@task_files.command(name="remove")
@click.argument("task_id")
@click.option("--files", required=True, help="Comma-separated relevant file paths to remove")
def task_files_remove(task_id: str, files: str) -> None:
    """Remove relevant file paths from a task."""
    task_item = _resolve_task_for_files(task_id)
    paths_to_remove = parse_relevant_files_csv(files)

    existing_paths = set(task_item.relevant_files)
    missing_paths = [path for path in paths_to_remove if path not in existing_paths]
    if missing_paths:
        raise click.ClickException(
            f"Task '{task_item.id}' does not include path(s): {', '.join(missing_paths)}"
        )

    remove_set = set(paths_to_remove)
    updated_paths = [path for path in task_item.relevant_files if path not in remove_set]
    task_item.update(relevant_files=updated_paths)
    cli_root.console.print(
        f"[green]Removed {len(paths_to_remove)} relevant file path(s) from task '{task_item.id}'.[/green]"
    )
