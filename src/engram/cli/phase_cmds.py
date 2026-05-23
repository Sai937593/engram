"""Phase command group registration."""

import click

import engram.cli as cli_root
from engram.cli.phase_helpers import normalize_phase_title
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
