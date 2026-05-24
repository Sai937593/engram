"""Mutation/lifecycle phase commands: add, update, start, and done."""

import click

import engram.cli as cli_root
from engram.cli.phase_cmds import phase
from engram.cli.phase_cmds_common import (
    VALID_PHASE_FIELDS,
    VALID_PHASE_STATUSES,
    print_demoted_phase_count,
    unfinished_linked_task_ids,
)
from engram.cli.phase_helpers import normalize_phase_title, resolve_phase_in_project
from engram.models.phase import Phase


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

    create_status = "planned" if status == "active" else status
    created_phase = Phase.create(
        project_id=project.id,
        title=title.strip(),
        description=description,
        status=create_status,
        order_index=order_index,
        acceptance=acceptance,
    )
    demoted_count = 0
    if status == "active":
        created_phase, demoted_count = Phase.start(created_phase.id)

    cli_root.console.print(f"[green]Phase created with ID:[/green] {created_phase.id}")
    print_demoted_phase_count(demoted_count)


@phase.command(name="update")
@click.argument("phase_ref")
@click.option("--field", help="Field to update")
@click.option("--value", help="New value for the field")
def phase_update(phase_ref: str, field: str | None, value: str | None) -> None:
    """Update a mutable phase field by ID or unique title."""
    project = cli_root.get_current_project()
    phase_item = resolve_phase_in_project(phase_ref, project.id)

    if not field or value is None:
        raise click.ClickException("Please provide both --field and --value.")

    if field not in VALID_PHASE_FIELDS:
        valid_fields = ", ".join(sorted(VALID_PHASE_FIELDS))
        raise click.ClickException(f"Unknown field '{field}'. Valid fields: {valid_fields}")

    update_value: str | int = value
    if field == "status":
        if value not in VALID_PHASE_STATUSES:
            valid_statuses = ", ".join(sorted(VALID_PHASE_STATUSES))
            raise click.ClickException(
                f"Invalid status '{value}'. Valid statuses: {valid_statuses}"
            )
    elif field == "order_index":
        try:
            update_value = int(value)
        except ValueError as exc:
            raise click.ClickException(
                f"Invalid order_index '{value}'. Provide an integer value."
            ) from exc
    elif field == "title":
        normalized_candidate = normalize_phase_title(value)
        if not normalized_candidate:
            raise click.ClickException("Phase title cannot be empty.")

        for existing_phase in Phase.list_by_project(project.id):
            if existing_phase.id == phase_item.id:
                continue
            if normalize_phase_title(existing_phase.title) == normalized_candidate:
                raise click.ClickException(
                    f"Phase title '{value}' already exists in this project as "
                    f"'{existing_phase.title}' ({existing_phase.id})."
                )
        update_value = value.strip()

    demoted_count = 0
    if field == "status" and update_value == "active":
        _, demoted_count = Phase.start(phase_item.id)
    else:
        phase_item.update(**{field: update_value})

    cli_root.console.print(f"[green]Phase '{phase_item.id}' updated.[/green]")
    print_demoted_phase_count(demoted_count)


@phase.command(name="start")
@click.argument("phase_ref")
def phase_start(phase_ref: str) -> None:
    """Start a phase by ID or unique title and make it the only active phase."""
    project = cli_root.get_current_project()
    phase_item = resolve_phase_in_project(phase_ref, project.id)

    started_phase, demoted_count = Phase.start(phase_item.id)

    cli_root.console.print(
        f"[green]Phase '{started_phase.title}' ({started_phase.id}) is now active.[/green]"
    )
    print_demoted_phase_count(demoted_count)


@phase.command(name="done")
@click.argument("phase_ref")
@click.option(
    "--evidence",
    required=True,
    help="Evidence of phase completion (test run, report, PR, etc.).",
)
@click.option(
    "--force",
    is_flag=True,
    help="Complete phase even when unfinished linked tasks remain.",
)
def phase_done(phase_ref: str, evidence: str, force: bool) -> None:
    """Mark a phase as done with evidence and optional guard override."""
    project = cli_root.get_current_project()
    phase_item = resolve_phase_in_project(phase_ref, project.id)

    cleaned_evidence = evidence.strip()
    if not cleaned_evidence:
        raise click.ClickException("Evidence cannot be empty.")

    blocking_task_ids = unfinished_linked_task_ids(project.id, phase_item)
    if blocking_task_ids and not force:
        raise click.ClickException(
            f"Cannot mark phase '{phase_item.title}' ({phase_item.id}) as done: "
            f"{len(blocking_task_ids)} unfinished linked task(s) remain "
            f"({', '.join(blocking_task_ids)}). Use --force to override."
        )

    phase_item.update(status="done", evidence=cleaned_evidence)
    cli_root.console.print(
        f"[green]Phase '{phase_item.title}' ({phase_item.id}) marked as done.[/green]"
    )
    if blocking_task_ids and force:
        cli_root.console.print(
            f"[yellow]Applied --force override with {len(blocking_task_ids)} unfinished linked task(s): "
            f"{', '.join(blocking_task_ids)}[/yellow]"
        )
