"""Project initialisation and management commands."""

import os

import click

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
