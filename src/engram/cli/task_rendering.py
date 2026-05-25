"""Rendering helpers for task CLI output."""

from rich.table import Table

import engram.cli as cli_root
from engram.cli.task_helpers import get_effective_status
from engram.models.project import Project
from engram.models.task import Task, get_effective_phase_title


def print_no_tasks_defined_message() -> None:
    """Print the standard guidance when a project has no tasks."""
    cli_root.console.print(
        "[yellow]No tasks defined.[/yellow] The next phase has not been planned yet."
    )
    cli_root.console.print("Action: Ask the user what the next phase of work should be, then run:")
    cli_root.console.print(
        '  [cyan]engram task add "<task title>" --phase "Phase N" --priority high[/cyan]'
    )


def status_counts(tasks: list[Task]) -> dict[str, int]:
    """Count tasks by effective status."""
    counts: dict[str, int] = {}
    for task in tasks:
        effective_status = get_effective_status(task)
        counts[effective_status] = counts.get(effective_status, 0) + 1
    return counts


def print_all_tasks_complete_message() -> None:
    """Print guidance when all tasks are completed."""
    cli_root.console.print("[green]All tasks complete.[/green] This phase is done.")
    cli_root.console.print(
        "Action: Confirm with the user whether to plan the next phase or close the project."
    )
    cli_root.console.print('  [cyan]engram task add "<next task>"[/cyan] to continue')


def print_all_tasks_complete_message_for_next() -> None:
    """Print completion guidance for the `task next` command."""
    cli_root.console.print("[green]All tasks complete.[/green] This phase is done.")
    cli_root.console.print(
        "Action: Confirm with the user whether to plan the next phase or close the project."
    )
    cli_root.console.print('  [cyan]engram task add "<next task>"[/cyan]  to continue')


def _task_status_style(status: str) -> str:
    if status == "blocked":
        return "red"
    if status == "done":
        return "blue"
    if status == "in-progress":
        return "yellow"
    if status == "cancelled":
        return "dim white"
    return "green"


def _format_status_display(task: Task, effective_status: str, include_dep_label: bool) -> str:
    status_display = effective_status
    if effective_status != task.status:
        status_display = (
            f"{effective_status} ({'dep' if include_dep_label else 'propagated from dependency'})"
        )
    status_style = _task_status_style(effective_status)
    return f"[{status_style}]{status_display}[/{status_style}]"


def render_task_table(project: Project, tasks: list[Task]) -> Table:
    """Build the task list table."""
    table = Table(
        title=f"Tasks for Project: {project.name}",
        header_style="bold green",
        border_style="green",
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Phase", style="blue")
    table.add_column("Status", style="bold green")
    table.add_column("Priority", style="yellow")
    table.add_column("Depends On", style="magenta")

    for task in tasks:
        effective_status = get_effective_status(task)
        priority_style = "bold red" if task.priority == "high" else "yellow"
        table.add_row(
            task.id,
            task.title,
            get_effective_phase_title(task) or "-",
            _format_status_display(task, effective_status, include_dep_label=True),
            f"[{priority_style}]{task.priority}[/{priority_style}]",
            task.depends_on or "-",
        )

    return table


def print_task_details(task: Task) -> None:
    """Print detailed information for a task."""
    cli_root.console.print(f"[cyan]ID:[/cyan] {task.id}")
    cli_root.console.print(f"[cyan]Title:[/cyan] {task.title}")

    effective_status = get_effective_status(task)
    status_display = effective_status
    if effective_status != task.status:
        status_display = f"{effective_status} (propagated from dependency)"
    cli_root.console.print(f"[cyan]Status:[/cyan] {status_display}")
    cli_root.console.print(f"[cyan]Priority:[/cyan] {task.priority}")
    cli_root.console.print(f"[cyan]Depends On:[/cyan] {task.depends_on or 'N/A'}")
    cli_root.console.print(f"[cyan]Phase:[/cyan] {get_effective_phase_title(task) or 'N/A'}")
    cli_root.console.print(f"[cyan]Description:[/cyan] {task.description or 'N/A'}")
    cli_root.console.print(f"[cyan]Acceptance Criteria:[/cyan]\n{task.acceptance or 'N/A'}")
    cli_root.console.print(f"[cyan]Evidence / Notes:[/cyan]\n{task.evidence or 'N/A'}")
    cli_root.console.print(f"[cyan]Tags:[/cyan] {', '.join(task.tags)}")
    if task.relevant_files:
        cli_root.console.print("[cyan]Relevant Files:[/cyan]")
        for path in task.relevant_files:
            cli_root.console.print(f"- {path}")


def print_next_task_details(task: Task) -> None:
    """Print compact details for the next task."""
    cli_root.console.print(f"[cyan]ID:[/cyan] {task.id}")
    cli_root.console.print(f"[cyan]Title:[/cyan] {task.title}")

    effective_status = get_effective_status(task)
    status_display = effective_status
    if effective_status != task.status:
        status_display = f"{effective_status} (dep)"
    cli_root.console.print(f"[cyan]Status:[/cyan] {status_display}")
    cli_root.console.print(f"[cyan]Priority:[/cyan] {task.priority}")
    cli_root.console.print(f"[cyan]Phase:[/cyan] {get_effective_phase_title(task) or 'N/A'}")
    cli_root.console.print(f"[cyan]Description:[/cyan] {task.description or 'N/A'}")
    cli_root.console.print(f"[cyan]Acceptance Criteria:[/cyan]\n{task.acceptance or 'N/A'}")
