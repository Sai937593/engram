"""Work session commands."""

import click
from rich.table import Table

import engram.cli as cli_root
from engram.models.session import Session


@cli_root.cli.group()
def session():
    """Manage work sessions."""
    pass


@session.command(name="start")
@click.option("--goal", prompt="Session goal", help="What are you trying to accomplish?")
def session_start(goal):
    """Start a new work session."""
    p = cli_root.get_current_project()
    active = Session.get_active(p.id)
    if active:
        cli_root.console.print(
            f"[yellow]An active session already exists:[/yellow] {active.id} (Goal: {active.goal})"
        )
        if click.confirm("Close it and start a new one?"):
            active.close(summary="Automatically closed to start new session.")
        else:
            return

    s = Session.create(project_id=p.id, goal=goal)
    cli_root.console.print(f"[green]Session started with ID:[/green] {s.id}")


@session.command(name="close")
@click.option("--summary", required=True, help="What did you accomplish? (required)")
@click.option("--next-steps", help="What are the next steps?")
def session_close(summary, next_steps):
    """Close the active work session. If none exists, auto-creates one."""
    p = cli_root.get_current_project()
    s = Session.get_active(p.id)
    if not s:
        s = Session.create(project_id=p.id, goal="(auto)")

    s.close(summary=summary, next_steps=next_steps)
    cli_root.console.print(f"[green]Session '{s.id}' closed.[/green]")


@session.command(name="list")
@click.option("--active", is_flag=True, help="Show only active (open) sessions")
def session_list(active):
    """List sessions for the current project (all by default)."""
    p = cli_root.get_current_project()
    sessions = Session.list_by_project(p.id)

    if active:
        sessions = [s for s in sessions if s.status == "open"]

    if not sessions:
        cli_root.console.print("No sessions found.")
        return

    table = Table(
        title=f"Sessions for Project: {p.name}", header_style="bold yellow", border_style="yellow"
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold green")
    table.add_column("Goal", style="white")
    table.add_column("Started At", style="dim yellow")

    for s in sessions:
        status_style = "green" if s.status == "open" else "dim blue"
        table.add_row(
            s.id, f"[{status_style}]{s.status}[/{status_style}]", s.goal or "N/A", s.started_at
        )

    cli_root.console.print(table)
