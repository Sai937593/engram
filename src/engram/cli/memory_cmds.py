"""Memory and type-specific memory commands."""

import click
from rich.table import Table

import engram.cli as cli_root
from engram.models.memory import Memory

VALID_MEMORY_FIELDS = {"title", "content", "type", "tags", "always_include"}
VALID_MEMORY_TYPES = {"note", "lesson", "decision", "constraint", "snippet"}


@cli_root.cli.group()
def memory() -> None:
    """Manage memories (freeform notes and snippets)."""
    pass


def _type_add(
    memory_type: str, title: str, content: str, tags: str | None, always_include: bool
) -> None:
    """Shared implementation for type-specific add commands."""
    p = cli_root.get_current_project()
    m = Memory.create(
        project_id=p.id,
        title=title,
        content=content,
        type=memory_type,
        tags=tags.split(",") if tags else [],
        always_include=always_include,
    )
    cli_root.console.print(f"[green]{memory_type.capitalize()} recorded with ID:[/green] {m.id}")


def _type_list(memory_type: str) -> None:
    """Shared implementation for type-specific list commands."""
    p = cli_root.get_current_project()
    memories = Memory.list_by_type(p.id, memory_type)
    if not memories:
        cli_root.console.print(f"No {memory_type}s found. Add one with: engram {memory_type} add")
        return
    label = memory_type.capitalize() + "s"
    table = Table(
        title=f"{label} for Project: {p.name}", header_style="bold magenta", border_style="magenta"
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Tags", style="dim blue")
    table.add_column("Always Include", style="dim")
    for m in memories:
        table.add_row(m.id, m.title, ", ".join(m.tags), "yes" if m.always_include else "no")
    cli_root.console.print(table)


def _type_search(memory_type: str, query: str) -> None:
    """Shared implementation for type-specific search commands."""
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
    for m in results:
        snippet = m.content.replace("\n", " ")
        table.add_row(m.id, m.title, snippet)
    cli_root.console.print(table)


def _type_get(memory_id: str) -> None:
    """Shared implementation for type-specific get commands."""
    m = Memory.get(memory_id)
    if not m:
        cli_root.console.print(f"[red]Error:[/red] Memory '{memory_id}' not found.")
        return
    _print_memory(m)


def _print_memory(m: Memory) -> None:
    cli_root.console.print(f"[cyan]ID:[/cyan] {m.id}")
    cli_root.console.print(f"[cyan]Title:[/cyan] {m.title}")
    cli_root.console.print(f"[cyan]Type:[/cyan] {m.type}")
    cli_root.console.print(f"[cyan]Tags:[/cyan] {', '.join(m.tags)}")
    cli_root.console.print(f"[cyan]Always Include:[/cyan] {m.always_include}")
    cli_root.console.print(f"[cyan]Content:[/cyan]\n{m.content}")


@cli_root.cli.group()
def constraint() -> None:
    """Constraints: hard rules agents must NEVER violate. Auto-surfaced at startup."""
    pass


@constraint.command(name="add")
@click.argument("title")
@click.option("--content", required=True, help="The rule and why it exists")
@click.option("--tags", help="Comma-separated tags")
@click.option("--no-always-include", is_flag=True, default=False, help="Don't always include")
def constraint_add(title: str, content: str, tags: str | None, no_always_include: bool) -> None:
    """Record a hard constraint (always shown at startup by default)."""
    _type_add("constraint", title, content, tags, always_include=not no_always_include)


@constraint.command(name="list")
def constraint_list() -> None:
    """List all constraints for this project."""
    _type_list("constraint")


@constraint.command(name="search")
@click.argument("query")
def constraint_search(query: str) -> None:
    """Search constraints using full-text search."""
    _type_search("constraint", query)


@constraint.command(name="get")
@click.argument("memory_id")
def constraint_get(memory_id: str) -> None:
    """Show full constraint detail."""
    _type_get(memory_id)


@cli_root.cli.group()
def lesson() -> None:
    """Lessons: solved problems agents should not re-solve. Auto-surfaced at startup."""
    pass


@lesson.command(name="add")
@click.argument("title")
@click.option("--content", required=True, help="What the problem was and how it was solved")
@click.option("--tags", help="Comma-separated tags")
@click.option("--no-always-include", is_flag=True, default=False, help="Don't always include")
def lesson_add(title: str, content: str, tags: str | None, no_always_include: bool) -> None:
    """Record a lesson learned (always shown at startup by default)."""
    _type_add("lesson", title, content, tags, always_include=not no_always_include)


@lesson.command(name="list")
def lesson_list() -> None:
    """List all lessons for this project."""
    _type_list("lesson")


@lesson.command(name="search")
@click.argument("query")
def lesson_search(query: str) -> None:
    """Search lessons using full-text search."""
    _type_search("lesson", query)


@lesson.command(name="get")
@click.argument("memory_id")
def lesson_get(memory_id: str) -> None:
    """Show full lesson detail."""
    _type_get(memory_id)


@cli_root.cli.group()
def decision() -> None:
    """Decisions: architectural choices with rationale. Auto-surfaced at startup."""
    pass


@decision.command(name="add")
@click.argument("title")
@click.option("--content", required=True, help="What was decided and why")
@click.option("--tags", help="Comma-separated tags")
@click.option("--no-always-include", is_flag=True, default=False, help="Don't always include")
def decision_add(title: str, content: str, tags: str | None, no_always_include: bool) -> None:
    """Record an architectural decision (always shown at startup by default)."""
    _type_add("decision", title, content, tags, always_include=not no_always_include)


@decision.command(name="list")
def decision_list() -> None:
    """List all decisions for this project."""
    _type_list("decision")


@decision.command(name="search")
@click.argument("query")
def decision_search(query: str) -> None:
    """Search decisions using full-text search."""
    _type_search("decision", query)


@decision.command(name="get")
@click.argument("memory_id")
def decision_get(memory_id: str) -> None:
    """Show full decision detail."""
    _type_get(memory_id)


@cli_root.cli.group()
def snippet() -> None:
    """Snippets: reusable commands, configs, and code patterns."""
    pass


@snippet.command(name="add")
@click.argument("title")
@click.option("--content", required=True, help="The reusable command or code")
@click.option("--tags", help="Comma-separated tags")
@click.option("--always-include", is_flag=True, default=False, help="Always include in context")
def snippet_add(title: str, content: str, tags: str | None, always_include: bool) -> None:
    """Record a reusable command or code snippet (search on demand)."""
    _type_add("snippet", title, content, tags, always_include=always_include)


@snippet.command(name="list")
def snippet_list() -> None:
    """List all snippets for this project."""
    _type_list("snippet")


@snippet.command(name="search")
@click.argument("query")
def snippet_search(query: str) -> None:
    """Search snippets using full-text search."""
    _type_search("snippet", query)


@snippet.command(name="get")
@click.argument("memory_id")
def snippet_get(memory_id: str) -> None:
    """Show full snippet detail."""
    _type_get(memory_id)


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
def memory_add(title, content, type, tags, always_include):
    """Add a new memory to the current project."""
    p = cli_root.get_current_project()
    m = Memory.create(
        project_id=p.id,
        title=title,
        content=content,
        type=type,
        tags=tags.split(",") if tags else [],
        always_include=always_include,
    )
    cli_root.console.print(f"[green]Memory created with ID:[/green] {m.id}")


@memory.command(name="list")
def memory_list():
    """List memories for the current project."""
    p = cli_root.get_current_project()
    memories = Memory.list_by_project(p.id)

    if not memories:
        cli_root.console.print("No memories found.")
        return

    table = Table(
        title=f"Memories for Project: {p.name}", header_style="bold blue", border_style="blue"
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Type", style="magenta")
    table.add_column("Tags", style="dim blue")

    for m in memories:
        table.add_row(m.id, m.title, m.type, ", ".join(m.tags))

    cli_root.console.print(table)


@memory.command(name="search")
@click.argument("query")
@click.option("--type", help="Filter by memory type")
@click.option("--tag", "tags", multiple=True, help="Filter by tag (can be used multiple times)")
def memory_search(query, type, tags):
    """Search memories using FTS5."""
    results = Memory.search(query, type_filter=type, tag_filters=tags)
    if not results:
        cli_root.console.print("No results found.")
        return

    table = Table(
        title=f"Search Results for: {query}", header_style="bold yellow", border_style="yellow"
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Snippet", style="dim")

    for m in results:
        snippet = m.content.replace("\n", " ")
        table.add_row(m.id, m.title, snippet)

    cli_root.console.print(table)


@memory.command(name="get")
@click.argument("memory_id")
def memory_get(memory_id):
    """Show memory details."""
    m = Memory.get(memory_id)
    if not m:
        cli_root.console.print(f"[red]Error:[/red] Memory '{memory_id}' not found.")
        return
    _print_memory(m)


@memory.command(name="update")
@click.argument("memory_id")
@click.option("--field", help="Field to update (title, content, type, tags, always_include)")
@click.option("--value", help="New value for the field")
def memory_update(memory_id, field, value):
    """Update a memory field."""
    m = Memory.get(memory_id)
    if not m:
        cli_root.console.print(f"[red]Error:[/red] Memory '{memory_id}' not found.")
        return

    if not field or value is None:
        cli_root.console.print("[yellow]Please provide both --field and --value.[/yellow]")
        return

    if field not in VALID_MEMORY_FIELDS:
        cli_root.console.print(
            f"[red]Error:[/red] Unknown field '{field}'. Valid fields: {', '.join(sorted(VALID_MEMORY_FIELDS))}"
        )
        return

    if field == "type" and value not in VALID_MEMORY_TYPES:
        cli_root.console.print(
            f"[red]Error:[/red] Invalid type '{value}'. Valid: {', '.join(sorted(VALID_MEMORY_TYPES))}"
        )
        return

    if field == "tags":
        value = value.split(",")
    elif field == "always_include":
        value = value.lower() in ("true", "1", "yes")

    m.update(**{field: value})
    cli_root.console.print(f"[green]Memory '{memory_id}' updated.[/green]")


@memory.command(name="delete")
@click.argument("memory_id")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
def memory_delete(memory_id, yes):
    """Delete a memory."""
    m = Memory.get(memory_id)
    if not m:
        cli_root.console.print(f"[red]Error:[/red] Memory '{memory_id}' not found.")
        return

    if yes or click.confirm(f"Are you sure you want to delete memory '{memory_id}'?"):
        m.delete()
        cli_root.console.print(f"[green]Memory '{memory_id}' deleted.[/green]")
