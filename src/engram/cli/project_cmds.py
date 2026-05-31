"""Project initialisation and management commands."""

import os

import click

import engram.cli as cli_root


@cli_root.cli.command()
@click.option("--name", prompt="Project name", help="Human-readable project name")
@click.option("--id", help="Unique project ID (slug)")
@click.option("--summary", help="Short project summary")
def init(name, id, summary):
    """Initialize engram in the current repository."""
    from engram.services.errors import EngramServiceError
    from engram.services.project_service import initialize_project

    cwd = os.getcwd()

    try:
        payload = initialize_project(cwd=cwd, name=name, project_id=id, summary=summary)
        if payload.get("created"):
            cli_root.console.print(
                f"[green]Initialized project '{payload['id']}' and bound to current directory.[/green]"
            )
        else:
            cli_root.console.print(
                f"[yellow]Current directory is already bound to project:[/yellow] {payload['id']} ({payload['name']})"
            )
    except EngramServiceError as e:
        cli_root.console.print(f"[red]Error:[/red] {e.message}")
        raise click.Abort() from e
