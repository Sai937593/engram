"""Context and export commands."""

import click

import engram.cli as cli_root
from engram.context import (
    get_handoff_context,
    get_snapshot_context,
    get_startup_context,
    get_task_context,
)


@cli_root.cli.group()
def context():
    """Generate context for agents."""
    pass


@context.command(name="startup")
def context_startup():
    """Generate project startup context."""
    p = cli_root.get_current_project()
    ctx = get_startup_context(p.id)
    cli_root.console.print(ctx)


@context.command(name="task")
@click.argument("task_id")
def context_task(task_id):
    """Generate task-specific context."""
    ctx = get_task_context(task_id)
    cli_root.console.print(ctx)


@cli_root.cli.group()
def export():
    """Export project data."""
    pass


@export.command(name="snapshot")
@click.option("--output", "-o", help="Output file path (default: SNAPSHOT.md)")
def export_snapshot(output):
    """Export a full project snapshot to Markdown."""
    p = cli_root.get_current_project()
    ctx = get_snapshot_context(p.id)

    filename = output or "SNAPSHOT.md"
    with open(filename, "w") as f:
        f.write(ctx)

    cli_root.console.print(f"[green]Snapshot exported to:[/green] {filename}")


@export.command(name="handoff")
@click.option("--output", "-o", help="Output file path (default: HANDOFF.md)")
def export_handoff(output):
    """Export a project handoff for another agent."""
    p = cli_root.get_current_project()
    ctx = get_handoff_context(p.id)

    filename = output or "HANDOFF.md"
    with open(filename, "w") as f:
        f.write(ctx)

    cli_root.console.print(f"[green]Handoff exported to:[/green] {filename}")
