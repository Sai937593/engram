"""Project initialisation and management commands."""

import os

import click
from rich.table import Table

import engram.cli as cli_root
from engram.models.project import Project


@cli_root.cli.command()
@click.option("--name", prompt="Project name", help="Human-readable project name")
@click.option("--id", help="Unique project ID (slug)")
@click.option("--summary", help="Short project summary")
def init(name, id, summary):
    """Initialize engram in the current repository."""
    cwd = os.getcwd()

    # Check if already registered
    existing = Project.find_by_repo_path(cwd)
    if existing:
        cli_root.console.print(
            f"[yellow]Current directory is already bound to project:[/yellow] {existing.id} ({existing.name})"
        )
        return

    if not id:
        # Simple slugify
        id = name.lower().replace(" ", "-")

    # Check if project ID already exists
    all_projects = Project.list_all()
    project = next((p for p in all_projects if p.id == id), None)

    if project:
        cli_root.console.print(
            f"[yellow]Project '{id}' already exists. Binding current directory to it.[/yellow]"
        )
        project.add_repo_path(cwd)
    else:
        Project.create(id, name, summary, repo_paths=[cwd])
        cli_root.console.print(
            f"[green]Initialized project '{id}' and bound to current directory.[/green]"
        )


@cli_root.cli.group()
def project():
    """Manage projects."""
    pass


@project.command(name="get")
def project_get():
    """Show current project details."""
    p = cli_root.get_current_project()
    cli_root.console.print(f"[cyan]ID:[/cyan] {p.id}")
    cli_root.console.print(f"[cyan]Name:[/cyan] {p.name}")
    cli_root.console.print(f"[cyan]Status:[/cyan] {p.status}")
    cli_root.console.print(f"[cyan]Summary:[/cyan] {p.summary or 'N/A'}")
    cli_root.console.print("[cyan]Repo Paths:[/cyan]")
    for path in p.repo_paths:
        cli_root.console.print(f"  - {path}")


@project.command(name="update")
@click.option("--name", help="New project name")
@click.option("--summary", help="New project summary")
@click.option(
    "--status", type=click.Choice(["active", "paused", "archived"]), help="New project status"
)
def project_update(name, summary, status):
    """Update current project details."""
    p = cli_root.get_current_project()
    if not any([name, summary, status]):
        cli_root.console.print("[yellow]No updates provided.[/yellow]")
        return

    p.update(name=name, summary=summary, status=status)
    cli_root.console.print(f"[green]Project '{p.id}' updated.[/green]")


@project.command(name="list")
def project_list():
    """List all registered projects."""
    projects = Project.list_all()
    if not projects:
        cli_root.console.print("No projects registered.")
        return

    table = Table(title="Engram Projects", header_style="bold magenta", border_style="cyan")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Repo Paths", style="dim")

    for p in projects:
        table.add_row(p.id, p.name, p.status, "\n".join(p.repo_paths))

    cli_root.console.print(table)
