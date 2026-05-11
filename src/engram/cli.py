import click
import os
from rich.console import Console
from rich.table import Table
from engram.db import init_db
from engram.models.project import Project

console = Console()

@click.group()
def cli():
    """Engram — Agentic persistent memory system."""
    init_db()

@cli.command()
@click.option("--name", prompt="Project name", help="Human-readable project name")
@click.option("--id", help="Unique project ID (slug)")
@click.option("--summary", help="Short project summary")
def init(name, id, summary):
    """Initialize engram in the current repository."""
    cwd = os.getcwd()
    
    # Check if already registered
    existing = Project.find_by_repo_path(cwd)
    if existing:
        console.print(f"[yellow]Current directory is already bound to project:[/yellow] {existing.id} ({existing.name})")
        return

    if not id:
        # Simple slugify
        id = name.lower().replace(" ", "-")
    
    # Check if project ID already exists
    all_projects = Project.list_all()
    project = next((p for p in all_projects if p.id == id), None)
    
    if project:
        console.print(f"[yellow]Project '{id}' already exists. Binding current directory to it.[/yellow]")
        project.add_repo_path(cwd)
    else:
        Project.create(id, name, summary, repo_paths=[cwd])
        console.print(f"[green]Initialized project '{id}' and bound to current directory.[/green]")

@cli.group()
def project():
    """Manage projects."""
    pass

def get_current_project():
    cwd = os.getcwd()
    project = Project.find_by_repo_path(cwd)
    if not project:
        console.print("[red]Error:[/red] Current directory is not bound to any Engram project.")
        console.print("Run 'engram init' to register this repository.")
        exit(1)
    return project

@project.command(name="get")
def project_get():
    """Show current project details."""
    p = get_current_project()
    console.print(f"[cyan]ID:[/cyan] {p.id}")
    console.print(f"[cyan]Name:[/cyan] {p.name}")
    console.print(f"[cyan]Status:[/cyan] {p.status}")
    console.print(f"[cyan]Summary:[/cyan] {p.summary or 'N/A'}")
    console.print(f"[cyan]Repo Paths:[/cyan]")
    for path in p.repo_paths:
        console.print(f"  - {path}")

@project.command(name="update")
@click.option("--name", help="New project name")
@click.option("--summary", help="New project summary")
@click.option("--status", type=click.Choice(['active', 'paused', 'archived']), help="New project status")
def project_update(name, summary, status):
    """Update current project details."""
    p = get_current_project()
    if not any([name, summary, status]):
        console.print("[yellow]No updates provided.[/yellow]")
        return
    
    p.update(name=name, summary=summary, status=status)
    console.print(f"[green]Project '{p.id}' updated.[/green]")

@project.command(name="list")
def project_list():
    """List all registered projects."""
    projects = Project.list_all()
    if not projects:
        console.print("No projects registered.")
        return

    table = Table(title="Engram Projects")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Repo Paths")

    for p in projects:
        table.add_row(p.id, p.name, p.status, "\n".join(p.repo_paths))

    console.print(table)

def main():
    cli()

if __name__ == "__main__":
    main()
