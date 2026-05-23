"""Phase command group registration."""

import click
from rich.table import Table

import engram.cli as cli_root
from engram.cli.phase_helpers import normalize_phase_title, resolve_phase_in_project
from engram.models.phase import Phase


@cli_root.cli.group()
def phase() -> None:
    """Manage phases."""
    pass


@phase.command(name="add")
@click.argument("title")
@click.option("--description", help="Phase description")
@click.option(
    "--status",
    type=click.Choice(["planned", "active", "done", "blocked", "cancelled"]),
    default="planned",
    show_default=True,
    help="Phase status",
)
@click.option("--acceptance", help="Acceptance criteria")
@click.option("--order-index", type=int, help="Manual phase ordering index")
def phase_add(
    title: str,
    description: str | None,
    status: str,
    acceptance: str | None,
    order_index: int | None,
) -> None:
    """Add a phase to the current project."""
    project = cli_root.get_current_project()
    normalized_title = normalize_phase_title(title)

    for existing_phase in Phase.list_by_project(project.id):
        if normalize_phase_title(existing_phase.title) == normalized_title:
            raise click.ClickException(
                f"Phase '{title}' already exists in this project as '{existing_phase.title}' ({existing_phase.id})."
            )

    created_phase = Phase.create(
        project_id=project.id,
        title=title.strip(),
        description=description,
        status=status,
        order_index=order_index,
        acceptance=acceptance,
    )
    cli_root.console.print(f"[green]Phase created with ID:[/green] {created_phase.id}")


def _compact_phase_summary(phase: Phase) -> str:
    summary_source = phase.description or phase.acceptance
    if not summary_source:
        return "-"

    compact = " ".join(summary_source.split())
    max_len = 72
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1] + "..."


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
            _compact_phase_summary(phase_item),
        )

    cli_root.console.print(table)


@phase.command(name="get")
@click.argument("phase_ref")
def phase_get(phase_ref: str) -> None:
    """Show full details for a phase by ID or unique title."""
    project = cli_root.get_current_project()
    phase = resolve_phase_in_project(phase_ref, project.id)

    cli_root.console.print(f"[cyan]ID:[/cyan] {phase.id}")
    cli_root.console.print(f"[cyan]Title:[/cyan] {phase.title}")
    cli_root.console.print(f"[cyan]Status:[/cyan] {phase.status}")
    cli_root.console.print(f"[cyan]Order Index:[/cyan] {phase.order_index}")
    cli_root.console.print(f"[cyan]Description:[/cyan] {phase.description or 'N/A'}")
    cli_root.console.print(f"[cyan]Acceptance Criteria:[/cyan]\n{phase.acceptance or 'N/A'}")
    cli_root.console.print(f"[cyan]Evidence / Notes:[/cyan]\n{phase.evidence or 'N/A'}")
