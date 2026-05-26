"""Shared helpers for memory CLI command modules."""

import click
from rich.table import Table

import engram.cli as cli_root
from engram.db import get_db_connection
from engram.models.memory import (
    VALID_MEMORY_SCOPES,
    Memory,
)
from engram.models.task import Task

VALID_MEMORY_FIELDS = {
    "title",
    "content",
    "type",
    "tags",
    "always_include",
    "scope",
    "level",
    "task_id",
}
VALID_MEMORY_TYPES = {"note", "lesson", "decision", "constraint", "snippet"}
DEFAULT_PROJECT_LEVEL_BY_TYPE = {
    "constraint": "L1",
    "decision": "L2",
    "lesson": "L3",
    "note": "L3",
    "snippet": "L3",
}
DEFAULT_TYPED_SCOPE_LEVEL_BY_TYPE = {
    "constraint": ("project", "L1"),
    "decision": ("project", "L2"),
    "lesson": ("task", None),
    "snippet": ("task", None),
}
NULLISH_VALUES = {"none", "null", "clear"}


def default_scope_level_for_type(memory_type: str) -> tuple[str, str]:
    """Return the default scope/level for memory creation without explicit flags."""
    return "project", DEFAULT_PROJECT_LEVEL_BY_TYPE.get(memory_type, "L3")


def default_typed_scope_level_for_type(memory_type: str) -> tuple[str, str | None]:
    """Return default scope/level for typed shortcut commands."""
    if memory_type in DEFAULT_TYPED_SCOPE_LEVEL_BY_TYPE:
        return DEFAULT_TYPED_SCOPE_LEVEL_BY_TYPE[memory_type]
    scope, level = default_scope_level_for_type(memory_type)
    return scope, level


def normalize_optional_value(value: str | None) -> str | None:
    """Normalize optional CLI values so blank/null-like strings become None."""
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.casefold() in NULLISH_VALUES:
        return None
    return normalized


def render_optional_value(value: str | None) -> str:
    """Render optional string values in CLI output with a consistent placeholder."""
    return value if value else "-"


def resolve_task_id_in_project(task_id: str | None, project_id: str) -> str | None:
    """Validate that task_id, when present, belongs to the active project."""
    normalized_task_id = normalize_optional_value(task_id)
    if normalized_task_id is None:
        return None

    task = Task.get(normalized_task_id)
    if not task or task.project_id != project_id:
        raise click.ClickException(f"Task '{normalized_task_id}' not found in the current project.")
    return task.id


def validate_memory_scope_contract(
    *,
    project_id: str,
    scope: str,
    level: str | None,
    task_id: str | None,
) -> tuple[str, str | None, str | None]:
    """Validate and normalize the shared memory scope/level/task contract."""
    normalized_scope = scope.strip().lower()
    if normalized_scope not in VALID_MEMORY_SCOPES:
        allowed = ", ".join(sorted(VALID_MEMORY_SCOPES))
        raise click.ClickException(f"Invalid memory scope '{scope}'. Allowed values: {allowed}.")

    try:
        normalized_level = Memory._validate_scope_level(scope=normalized_scope, level=level)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    normalized_task_id = resolve_task_id_in_project(task_id, project_id)
    return normalized_scope, normalized_level, normalized_task_id


def resolve_memory_add_contract(
    *,
    project_id: str,
    memory_type: str,
    scope: str | None,
    level: str | None,
    task_id: str | None,
) -> tuple[str, str | None, str | None]:
    """Resolve and validate memory add scope inputs with backward-compatible defaults."""
    requested_scope = normalize_optional_value(scope)
    if requested_scope is None:
        requested_scope = default_scope_level_for_type(memory_type)[0]

    requested_level = level
    if level is None and requested_scope == "project":
        if normalize_optional_value(scope) is None:
            requested_level = default_scope_level_for_type(memory_type)[1]

    return validate_memory_scope_contract(
        project_id=project_id,
        scope=requested_scope,
        level=requested_level,
        task_id=task_id,
    )


def resolve_typed_memory_add_contract(
    *,
    project_id: str,
    memory_type: str,
    scope: str | None = None,
    level: str | None = None,
    task_id: str | None = None,
) -> tuple[str, str | None, str | None]:
    """Resolve typed command defaults while honoring explicit scope/level/task overrides."""
    requested_scope = normalize_optional_value(scope)
    typed_default_scope, typed_default_level = default_typed_scope_level_for_type(memory_type)
    if requested_scope is None:
        requested_scope = typed_default_scope

    requested_level = level
    if requested_level is None and requested_scope == "project":
        if requested_scope == typed_default_scope:
            requested_level = typed_default_level
        else:
            requested_level = DEFAULT_PROJECT_LEVEL_BY_TYPE.get(memory_type, "L3")

    requested_task_id = task_id
    if requested_scope == "task" and normalize_optional_value(requested_task_id) is None:
        tasks = Task.list_by_project(project_id)
        in_progress_tasks = [task for task in tasks if task.status == "in-progress"]
        if len(in_progress_tasks) == 1:
            requested_task_id = in_progress_tasks[0].id

    return validate_memory_scope_contract(
        project_id=project_id,
        scope=requested_scope,
        level=requested_level,
        task_id=requested_task_id,
    )


def resolve_memory_update_field_value(
    *,
    project_id: str,
    memory: Memory,
    field: str,
    value: str,
) -> dict[str, str | list[str] | bool | None]:
    """Convert and validate a memory update field/value payload."""
    if field == "tags":
        return {"tags": value.split(",")}

    if field == "always_include":
        return {"always_include": value.lower() in ("true", "1", "yes")}

    if field == "task_id":
        normalized_task_id = resolve_task_id_in_project(value, project_id)
        return {"task_id": normalized_task_id}

    if field not in {"scope", "level"}:
        return {field: value}

    next_scope = memory.scope
    next_level = memory.level
    next_task_id = memory.task_id

    if field == "scope":
        next_scope = value
        if normalize_optional_value(value) == "task":
            next_level = None
        elif normalize_optional_value(value) == "project" and memory.level is None:
            next_level = default_scope_level_for_type(memory.type)[1]
    elif field == "level":
        next_level = value

    normalized_scope, normalized_level, normalized_task_id = validate_memory_scope_contract(
        project_id=project_id,
        scope=next_scope,
        level=next_level,
        task_id=next_task_id,
    )
    return {"scope": normalized_scope, "level": normalized_level, "task_id": normalized_task_id}


def print_memory_details(memory: Memory) -> None:
    """Render a single memory in full detail."""
    cli_root.console.print(f"[cyan]ID:[/cyan] {memory.id}")
    cli_root.console.print(f"[cyan]Title:[/cyan] {memory.title}")
    cli_root.console.print(f"[cyan]Type:[/cyan] {memory.type}")
    cli_root.console.print(f"[cyan]Scope:[/cyan] {memory.scope}")
    cli_root.console.print(f"[cyan]Level:[/cyan] {render_optional_value(memory.level)}")
    cli_root.console.print(f"[cyan]Task ID:[/cyan] {render_optional_value(memory.task_id)}")
    cli_root.console.print(f"[cyan]Tags:[/cyan] {render_optional_value(', '.join(memory.tags))}")
    cli_root.console.print(f"[cyan]Always Include:[/cyan] {memory.always_include}")
    cli_root.console.print(f"[cyan]Content:[/cyan]\n{memory.content}")


def get_memory_or_print_error(memory_id: str) -> Memory | None:
    """Fetch a memory by ID and print a standard not-found message."""
    memory = Memory.get(memory_id)
    if not memory:
        cli_root.console.print(f"[red]Error:[/red] Memory '{memory_id}' not found.")
        return None
    return memory


def resolve_memory_id_in_project(value: str, project_id: str) -> str:
    """Resolve a memory ID or prefix to a unique memory in the current project."""
    normalized_value = value.strip()
    if not normalized_value:
        raise click.ClickException("Memory reference cannot be empty.")

    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id FROM memories WHERE project_id = ? AND (id = ? OR id LIKE ?)",
        (project_id, normalized_value, normalized_value + "%"),
    ).fetchall()
    conn.close()

    matching_ids = sorted({row["id"] for row in rows})
    if not matching_ids:
        conn = get_db_connection()
        global_rows = conn.execute(
            "SELECT id FROM memories WHERE id = ? OR id LIKE ?",
            (normalized_value, normalized_value + "%"),
        ).fetchall()
        conn.close()
        if global_rows:
            raise click.ClickException(
                f"Memory '{normalized_value}' is a foreign memory belonging to another project."
            )
        raise click.ClickException(f"Memory '{normalized_value}' not found in the current project.")

    if len(matching_ids) > 1 and normalized_value not in matching_ids:
        raise click.ClickException(
            f"Ambiguous memory '{normalized_value}'. Multiple matches found: {', '.join(matching_ids)}"
        )

    if normalized_value in matching_ids:
        return normalized_value
    return matching_ids[0]


def add_typed_memory(
    memory_type: str,
    title: str,
    content: str,
    tags: str | None,
    always_include: bool,
    scope: str | None = None,
    level: str | None = None,
    task_id: str | None = None,
) -> None:
    """Create a memory entry for a typed command group."""
    project = cli_root.get_current_project()
    normalized_scope, normalized_level, normalized_task_id = resolve_typed_memory_add_contract(
        project_id=project.id,
        memory_type=memory_type,
        scope=scope,
        level=level,
        task_id=task_id,
    )
    memory = Memory.create(
        project_id=project.id,
        title=title,
        content=content,
        type=memory_type,
        scope=normalized_scope,
        level=normalized_level,
        task_id=normalized_task_id,
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
    table.add_column("Scope", style="green")
    table.add_column("Level", style="blue")
    table.add_column("Task ID", style="cyan")
    table.add_column("Tags", style="dim blue")
    table.add_column("Always Include", style="dim")
    for memory in memories:
        table.add_row(
            memory.id,
            memory.title,
            memory.scope,
            render_optional_value(memory.level),
            render_optional_value(memory.task_id),
            render_optional_value(", ".join(memory.tags)),
            "yes" if memory.always_include else "no",
        )
    cli_root.console.print(table)


def search_typed_memories(memory_type: str, query: str) -> None:
    """Search typed memories with full-text search."""
    project = cli_root.get_current_project()
    results = Memory.search(query, type_filter=memory_type, project_id=project.id)
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
