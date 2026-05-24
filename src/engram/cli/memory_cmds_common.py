"""Shared helpers for memory CLI command modules."""

from rich.table import Table

import engram.cli as cli_root
from engram.models.memory import Memory

VALID_MEMORY_FIELDS = {"title", "content", "type", "tags", "always_include"}
VALID_MEMORY_TYPES = {"note", "lesson", "decision", "constraint", "snippet"}
DEFAULT_PROJECT_LEVEL_BY_TYPE = {
    "constraint": "L1",
    "decision": "L2",
    "lesson": "L3",
    "note": "L3",
    "snippet": "L3",
}


def default_scope_level_for_type(memory_type: str) -> tuple[str, str]:
    """Return the default scope/level for memory creation without explicit flags."""
    return "project", DEFAULT_PROJECT_LEVEL_BY_TYPE.get(memory_type, "L3")


def print_memory_details(memory: Memory) -> None:
    """Render a single memory in full detail."""
    cli_root.console.print(f"[cyan]ID:[/cyan] {memory.id}")
    cli_root.console.print(f"[cyan]Title:[/cyan] {memory.title}")
    cli_root.console.print(f"[cyan]Type:[/cyan] {memory.type}")
    cli_root.console.print(f"[cyan]Tags:[/cyan] {', '.join(memory.tags)}")
    cli_root.console.print(f"[cyan]Always Include:[/cyan] {memory.always_include}")
    cli_root.console.print(f"[cyan]Content:[/cyan]\n{memory.content}")


def get_memory_or_print_error(memory_id: str) -> Memory | None:
    """Fetch a memory by ID and print a standard not-found message."""
    memory = Memory.get(memory_id)
    if not memory:
        cli_root.console.print(f"[red]Error:[/red] Memory '{memory_id}' not found.")
        return None
    return memory


def add_typed_memory(
    memory_type: str,
    title: str,
    content: str,
    tags: str | None,
    always_include: bool,
) -> None:
    """Create a memory entry for a typed command group."""
    project = cli_root.get_current_project()
    scope, level = default_scope_level_for_type(memory_type)
    memory = Memory.create(
        project_id=project.id,
        title=title,
        content=content,
        type=memory_type,
        scope=scope,
        level=level,
        tags=tags.split(",") if tags else [],
        always_include=always_include,
    )
    cli_root.console.print(
        f"[green]{memory_type.capitalize()} recorded with ID:[/green] {memory.id}"
    )


def list_typed_memories(memory_type: str) -> None:
    """List memories for a typed command group."""
    project = cli_root.get_current_project()
    memories = Memory.list_by_type(project.id, memory_type)
    if not memories:
        cli_root.console.print(f"No {memory_type}s found. Add one with: engram {memory_type} add")
        return

    label = memory_type.capitalize() + "s"
    table = Table(
        title=f"{label} for Project: {project.name}",
        header_style="bold magenta",
        border_style="magenta",
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Tags", style="dim blue")
    table.add_column("Always Include", style="dim")
    for memory in memories:
        table.add_row(
            memory.id,
            memory.title,
            ", ".join(memory.tags),
            "yes" if memory.always_include else "no",
        )
    cli_root.console.print(table)


def search_typed_memories(memory_type: str, query: str) -> None:
    """Search typed memories with full-text search."""
    results = Memory.search(query, type_filter=memory_type)
    if not results:
        cli_root.console.print(f"No {memory_type}s found matching '{query}'.")
        return

    table = Table(
        title=f"{memory_type.capitalize()} Search: {query}",
        header_style="bold yellow",
        border_style="yellow",
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Snippet", style="dim")
    for memory in results:
        snippet = memory.content.replace("\n", " ")
        table.add_row(memory.id, memory.title, snippet)
    cli_root.console.print(table)


def get_and_print_typed_memory(memory_id: str) -> None:
    """Render full details for a single typed memory entry."""
    memory = get_memory_or_print_error(memory_id)
    if memory:
        print_memory_details(memory)
