"""Generic memory commands under ``engram memory``."""

import click
from rich.table import Table

import engram.cli as cli_root
from engram.cli.memory_cmds import memory
from engram.cli.memory_cmds_common import (
    VALID_MEMORY_FIELDS,
    VALID_MEMORY_TYPES,
    get_memory_or_print_error,
    print_memory_details,
    render_optional_value,
    resolve_memory_add_contract,
    resolve_memory_update_field_value,
)
from engram.db import get_db_connection
from engram.memory_retrieval.startup_orchestration import (
    orchestrate_startup_task_memory_retrieval,
)
from engram.models.memory import Memory
from engram.models.task import Task


@memory.command(name="add")
@click.argument("title")
@click.option("--content", required=True, help="Memory content (required)")
@click.option(
    "--type",
    default="note",
    type=click.Choice(["note", "lesson", "decision", "constraint", "snippet"]),
    help="Memory type",
)
@click.option("--tags", help="Comma-separated tags")
@click.option("--always-include", is_flag=True, help="Always include in context")
@click.option("--scope", help="Memory scope (project or task)")
@click.option("--level", help="Project memory level (L0, L1, L2, L3)")
@click.option("--task-id", help="Optional linked/origin task ID")
def memory_add(
    title: str,
    content: str,
    type: str,
    tags: str | None,
    always_include: bool,
    scope: str | None,
    level: str | None,
    task_id: str | None,
) -> None:
    """Add a new memory to the current project."""
    project = cli_root.get_current_project()
    normalized_scope, normalized_level, normalized_task_id = resolve_memory_add_contract(
        project_id=project.id,
        memory_type=type,
        scope=scope,
        level=level,
        task_id=task_id,
    )
    memory_item = Memory.create(
        project_id=project.id,
        title=title,
        content=content,
        type=type,
        scope=normalized_scope,
        level=normalized_level,
        task_id=normalized_task_id,
        tags=tags.split(",") if tags else [],
        always_include=always_include,
    )
    cli_root.console.print(f"[green]Memory created with ID:[/green] {memory_item.id}")


@memory.command(name="list")
def memory_list() -> None:
    """List memories for the current project."""
    project = cli_root.get_current_project()
    memories = Memory.list_by_project(project.id)
    if not memories:
        cli_root.console.print("No memories found.")
        return

    table = Table(
        title=f"Memories for Project: {project.name}",
        header_style="bold blue",
        border_style="blue",
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Type", style="magenta")
    table.add_column("Scope", style="green")
    table.add_column("Level", style="blue")
    table.add_column("Task ID", style="cyan")
    table.add_column("Tags", style="dim blue")
    for memory_item in memories:
        table.add_row(
            memory_item.id,
            memory_item.title,
            memory_item.type,
            memory_item.scope,
            render_optional_value(memory_item.level),
            render_optional_value(memory_item.task_id),
            render_optional_value(", ".join(memory_item.tags)),
        )
    cli_root.console.print(table)


@memory.command(name="search")
@click.argument("query")
@click.option("--type", help="Filter by memory type")
@click.option("--tag", "tags", multiple=True, help="Filter by tag (can be used multiple times)")
def memory_search(query: str, type: str | None, tags: tuple[str, ...]) -> None:
    """Search memories using FTS5."""
    results = Memory.search(query, type_filter=type, tag_filters=tags)
    if not results:
        cli_root.console.print("No results found.")
        return

    table = Table(
        title=f"Search Results for: {query}",
        header_style="bold yellow",
        border_style="yellow",
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Snippet", style="dim")
    for memory_item in results:
        snippet = memory_item.content.replace("\n", " ")
        table.add_row(memory_item.id, memory_item.title, snippet)
    cli_root.console.print(table)


@memory.command(name="get")
@click.argument("memory_id")
def memory_get(memory_id: str) -> None:
    """Show memory details."""
    memory_item = get_memory_or_print_error(memory_id)
    if memory_item:
        print_memory_details(memory_item)


@memory.command(name="update")
@click.argument("memory_id")
@click.option(
    "--field",
    help="Field to update (title, content, type, tags, always_include, scope, level, task_id)",
)
@click.option("--value", help="New value for the field")
def memory_update(memory_id: str, field: str | None, value: str | None) -> None:
    """Update a memory field."""
    project = cli_root.get_current_project()
    memory_item = get_memory_or_print_error(memory_id)
    if not memory_item:
        return

    if not field or value is None:
        cli_root.console.print("[yellow]Please provide both --field and --value.[/yellow]")
        return

    if field not in VALID_MEMORY_FIELDS:
        valid_fields = ", ".join(sorted(VALID_MEMORY_FIELDS))
        cli_root.console.print(
            f"[red]Error:[/red] Unknown field '{field}'. Valid fields: {valid_fields}"
        )
        return

    if field == "type" and value not in VALID_MEMORY_TYPES:
        valid_types = ", ".join(sorted(VALID_MEMORY_TYPES))
        cli_root.console.print(f"[red]Error:[/red] Invalid type '{value}'. Valid: {valid_types}")
        return

    update_payload = resolve_memory_update_field_value(
        project_id=project.id,
        memory=memory_item,
        field=field,
        value=value,
    )
    memory_item.update(**update_payload)
    cli_root.console.print(f"[green]Memory '{memory_id}' updated.[/green]")


@memory.command(name="delete")
@click.argument("memory_id")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
def memory_delete(memory_id: str, yes: bool) -> None:
    """Delete a memory."""
    memory_item = get_memory_or_print_error(memory_id)
    if not memory_item:
        return

    if yes or click.confirm(f"Are you sure you want to delete memory '{memory_id}'?"):
        memory_item.delete()
        cli_root.console.print(f"[green]Memory '{memory_id}' deleted.[/green]")


def resolve_task_by_id_or_prefix(project_id: str, value: str) -> Task:
    """Resolve a task ID or prefix safely within the current project, showing clear missing/foreign errors."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id FROM tasks WHERE project_id = ? AND (id = ? OR id LIKE ?)",
        (project_id, value, value + "%"),
    ).fetchall()
    conn.close()

    matching_ids = sorted(list(set(row["id"] for row in rows)))

    if not matching_ids:
        # Check if it exists in another project (foreign check)
        conn = get_db_connection()
        global_rows = conn.execute(
            "SELECT id FROM tasks WHERE id = ? OR id LIKE ?",
            (value, value + "%"),
        ).fetchall()
        conn.close()
        if global_rows:
            raise click.ClickException(
                f"Task '{value}' is a foreign task belonging to another project."
            )
        else:
            raise click.ClickException(f"Task '{value}' not found in the current project.")

    if len(matching_ids) > 1:
        if value in matching_ids:
            resolved_id = value
        else:
            raise click.ClickException(
                f"Ambiguous task ID '{value}'. Multiple matches found: {', '.join(matching_ids)}"
            )
    else:
        resolved_id = matching_ids[0]

    task_item = Task.get(resolved_id)
    if not task_item:
        raise click.ClickException(f"Task '{value}' not found in the current project.")
    return task_item


@memory.command(name="related-to-task")
@click.argument("task_id")
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Print retrieval query, candidate, and packing diagnostics.",
)
def memory_related_to_task(task_id: str, debug: bool) -> None:
    """Inspect related memories for a task without mutating state."""
    project = cli_root.get_current_project()
    task_item = resolve_task_by_id_or_prefix(project.id, task_id)

    # Try resolving active phase if it matches the task's phase context
    from engram.cli.work_cmds_helpers import format_retrieval_debug_output, get_active_phase

    active_phase = get_active_phase(project.id)
    if active_phase:
        # If the task doesn't belong to the active phase, do not pass active_phase
        if not (
            task_item.phase_id == active_phase.id
            or (
                not task_item.phase_id
                and task_item.phase
                and task_item.phase.strip().casefold() == active_phase.title.strip().casefold()
            )
        ):
            active_phase = None

    # Execute query -> retriever -> packer pipeline
    result = orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=active_phase,
        selected_task=task_item,
    )

    if debug:
        cli_root.console.print(format_retrieval_debug_output(result))

    packed_items = result.pack_result.items
    if not packed_items:
        if not debug:
            cli_root.console.print("No relevant task memories selected.")
        return

    # Render using premium Rich Table
    table = Table(
        title=f"Related Memories for Task '{task_item.id}': {task_item.title}",
        header_style="bold cyan",
        border_style="cyan",
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Type", style="magenta")
    table.add_column("Content", style="dim")
    table.add_column("Boost", style="green", justify="right")
    table.add_column("FTS Rank", style="yellow", justify="right")

    for item in packed_items:
        table.add_row(
            item.memory_id,
            item.title,
            item.type,
            item.content.replace("\n", " "),
            str(item.boost_score),
            f"{item.fts_rank:.6f}",
        )

    cli_root.console.print(table)
