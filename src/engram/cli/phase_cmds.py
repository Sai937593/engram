"""Phase command group registration."""

import click
from rich.table import Table

import engram.cli as cli_root
from engram.cli.phase_helpers import normalize_phase_title, resolve_phase_in_project
from engram.models.phase import Phase
from engram.models.task import Task

VALID_PHASE_FIELDS = {"title", "description", "status", "order_index", "acceptance", "evidence"}
VALID_PHASE_STATUSES = {"planned", "active", "done", "blocked", "cancelled"}


def _print_demoted_phase_count(demoted_count: int) -> None:
    """Print a summary when activation demotes existing active phases."""
    if not demoted_count:
        return

    noun = "phase" if demoted_count == 1 else "phases"
    cli_root.console.print(
        f"[yellow]Demoted {demoted_count} previously active {noun} to planned.[/yellow]"
    )


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
    _print_demoted_phase_count(demoted_count)


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


@phase.command(name="update")
@click.argument("phase_ref")
@click.option("--field", help="Field to update")
@click.option("--value", help="New value for the field")
def phase_update(phase_ref: str, field: str | None, value: str | None) -> None:
    """Update a mutable phase field by ID or unique title."""
    project = cli_root.get_current_project()
    phase = resolve_phase_in_project(phase_ref, project.id)

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
            if existing_phase.id == phase.id:
                continue
            if normalize_phase_title(existing_phase.title) == normalized_candidate:
                raise click.ClickException(
                    f"Phase title '{value}' already exists in this project as "
                    f"'{existing_phase.title}' ({existing_phase.id})."
                )
        update_value = value.strip()

    demoted_count = 0
    if field == "status" and update_value == "active":
        _, demoted_count = Phase.start(phase.id)
    else:
        phase.update(**{field: update_value})

    cli_root.console.print(f"[green]Phase '{phase.id}' updated.[/green]")
    _print_demoted_phase_count(demoted_count)


@phase.command(name="start")
@click.argument("phase_ref")
def phase_start(phase_ref: str) -> None:
    """Start a phase by ID or unique title and make it the only active phase."""
    project = cli_root.get_current_project()
    phase = resolve_phase_in_project(phase_ref, project.id)

    started_phase, demoted_count = Phase.start(phase.id)

    cli_root.console.print(
        f"[green]Phase '{started_phase.title}' ({started_phase.id}) is now active.[/green]"
    )
    _print_demoted_phase_count(demoted_count)


def _task_is_linked_to_phase(task: Task, phase: Phase) -> bool:
    """Return whether a task is linked to a phase via phase_id or legacy phase title."""
    if task.phase_id == phase.id:
        return True
    if task.phase_id:
        return False
    return normalize_phase_title(task.phase) == normalize_phase_title(phase.title)


def _unfinished_linked_task_ids(project_id: str, phase: Phase) -> list[str]:
    """Return unfinished task IDs linked to a phase in the current project."""
    blocking_statuses = {"todo", "in-progress", "blocked"}
    linked_blockers: list[str] = []

    for task in Task.list_by_project(project_id):
        if task.status not in blocking_statuses:
            continue
        if _task_is_linked_to_phase(task, phase):
            linked_blockers.append(task.id)

    return sorted(linked_blockers)


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
    phase = resolve_phase_in_project(phase_ref, project.id)

    cleaned_evidence = evidence.strip()
    if not cleaned_evidence:
        raise click.ClickException("Evidence cannot be empty.")

    blocking_task_ids = _unfinished_linked_task_ids(project.id, phase)
    if blocking_task_ids and not force:
        raise click.ClickException(
            f"Cannot mark phase '{phase.title}' ({phase.id}) as done: "
            f"{len(blocking_task_ids)} unfinished linked task(s) remain "
            f"({', '.join(blocking_task_ids)}). Use --force to override."
        )

    phase.update(status="done", evidence=cleaned_evidence)
    cli_root.console.print(f"[green]Phase '{phase.title}' ({phase.id}) marked as done.[/green]")
    if blocking_task_ids and force:
        cli_root.console.print(
            f"[yellow]Applied --force override with {len(blocking_task_ids)} unfinished linked task(s): "
            f"{', '.join(blocking_task_ids)}[/yellow]"
        )
