"""Context and export commands."""

import click

import engram.cli as cli_root
from engram.services import (
    get_handoff_context_for_current_project,
    get_snapshot_context_for_current_project,
    get_startup_context_for_current_project,
    get_task_context_for_current_project,
)
from engram.services.errors import EngramServiceError


@cli_root.cli.group()
def context() -> None:
    """Generate context for agents."""
    pass


@context.command(name="startup")
def context_startup() -> None:
    """Generate project startup context."""
    try:
        ctx = get_startup_context_for_current_project()
    except EngramServiceError as err:
        raise click.ClickException(err.message) from err
    cli_root.console.print(ctx)


@context.command(name="task")
@click.argument("task_id")
def context_task(task_id: str) -> None:
    """Generate task-specific context."""
    try:
        ctx = get_task_context_for_current_project(task_ref=task_id)
    except EngramServiceError as err:
        raise click.ClickException(err.message) from err
    cli_root.console.print(ctx)


@cli_root.cli.group()
def export() -> None:
    """Export project data."""
    pass


@export.command(name="snapshot")
@click.option("--output", "-o", help="Output file path (default: SNAPSHOT.md)")
def export_snapshot(output: str | None) -> None:
    """Export a full project snapshot to Markdown."""
    try:
        ctx = get_snapshot_context_for_current_project()
    except EngramServiceError as err:
        raise click.ClickException(err.message) from err

    filename = output or "SNAPSHOT.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(ctx)

    cli_root.console.print(f"[green]Snapshot exported to:[/green] {filename}")


@export.command(name="handoff")
@click.option("--output", "-o", help="Output file path (default: HANDOFF.md)")
def export_handoff(output: str | None) -> None:
    """Export a project handoff for another agent."""
    try:
        ctx = get_handoff_context_for_current_project()
    except EngramServiceError as err:
        raise click.ClickException(err.message) from err

    filename = output or "HANDOFF.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(ctx)

    cli_root.console.print(f"[green]Handoff exported to:[/green] {filename}")
