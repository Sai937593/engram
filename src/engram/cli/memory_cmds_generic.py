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
)
from engram.models.memory import Memory


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
def memory_add(
    title: str,
    content: str,
    type: str,
    tags: str | None,
    always_include: bool,
) -> None:
    """Add a new memory to the current project."""
    project = cli_root.get_current_project()
    memory_item = Memory.create(
        project_id=project.id,
        title=title,
        content=content,
        type=type,
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
    table.add_column("Tags", style="dim blue")
    for memory_item in memories:
        table.add_row(
            memory_item.id, memory_item.title, memory_item.type, ", ".join(memory_item.tags)
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
@click.option("--field", help="Field to update (title, content, type, tags, always_include)")
@click.option("--value", help="New value for the field")
def memory_update(memory_id: str, field: str | None, value: str | None) -> None:
    """Update a memory field."""
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

    converted_value: str | list[str] | bool = value
    if field == "tags":
        converted_value = value.split(",")
    elif field == "always_include":
        converted_value = value.lower() in ("true", "1", "yes")

    memory_item.update(**{field: converted_value})
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
