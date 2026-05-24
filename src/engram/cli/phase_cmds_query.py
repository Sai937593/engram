"""Read/query phase commands: list and get."""

import click
from rich.table import Table

import engram.cli as cli_root
from engram.cli.phase_cmds import phase
from engram.cli.phase_cmds_common import compact_phase_summary
from engram.cli.phase_helpers import resolve_phase_in_project
from engram.models.phase import Phase


@phase.command(name="list")
def phase_list() -> None:
    """List phases for the current project."""
    project = cli_root.get_current_project()
    phases = Phase.list_by_project(project.id)

    if not phases:
        cli_root.console.print("[yellow]No phases defined for this project.[/yellow]")
        return

    table = Table(
        title=f"Phases for Project: {project.name}",
        header_style="bold green",
        border_style="green",
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Status", style="bold green")
    table.add_column("Order", style="yellow", justify="right")
    table.add_column("Summary", style="blue")

    for phase_item in phases:
        status_style = "green"
        if phase_item.status in {"blocked", "cancelled"}:
            status_style = "red" if phase_item.status == "blocked" else "dim white"
        elif phase_item.status == "done":
            status_style = "blue"
        elif phase_item.status == "active":
            status_style = "yellow"

        table.add_row(
            phase_item.id,
            phase_item.title,
            f"[{status_style}]{phase_item.status}[/{status_style}]",
            str(phase_item.order_index),
            compact_phase_summary(phase_item),
        )

    cli_root.console.print(table)


@phase.command(name="get")
@click.argument("phase_ref")
def phase_get(phase_ref: str) -> None:
    """Show full details for a phase by ID or unique title."""
    project = cli_root.get_current_project()
    phase_item = resolve_phase_in_project(phase_ref, project.id)

    cli_root.console.print(f"[cyan]ID:[/cyan] {phase_item.id}")
    cli_root.console.print(f"[cyan]Title:[/cyan] {phase_item.title}")
    cli_root.console.print(f"[cyan]Status:[/cyan] {phase_item.status}")
    cli_root.console.print(f"[cyan]Order Index:[/cyan] {phase_item.order_index}")
    cli_root.console.print(f"[cyan]Description:[/cyan] {phase_item.description or 'N/A'}")
    cli_root.console.print(f"[cyan]Acceptance Criteria:[/cyan]\n{phase_item.acceptance or 'N/A'}")
    cli_root.console.print(f"[cyan]Evidence / Notes:[/cyan]\n{phase_item.evidence or 'N/A'}")
