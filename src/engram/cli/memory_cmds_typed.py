"""Type-specific memory command groups and handlers."""

import click

import engram.cli as cli_root
from engram.cli.memory_cmds_common import (
    add_typed_memory,
    get_and_print_typed_memory,
    list_typed_memories,
    search_typed_memories,
)


def _resolve_typed_override_scope(
    *,
    scope: str | None,
    project_scope: bool,
    level: str | None,
    command_name: str,
) -> str | None:
    """Resolve explicit typed override inputs into an effective memory scope."""
    normalized_scope = scope.lower() if scope else None
    if project_scope and normalized_scope == "task":
        raise click.ClickException(
            f"{command_name} add received conflicting scope flags: use either --scope task or --project."
        )
    if project_scope:
        normalized_scope = "project"

    if level is not None and normalized_scope is None:
        normalized_scope = "project"

    if normalized_scope == "project" and level is None:
        raise click.ClickException(
            f"Project-scope {command_name}s require --level (L0, L1, L2, or L3)."
        )
    return normalized_scope


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
    add_typed_memory("constraint", title, content, tags, always_include=not no_always_include)


@constraint.command(name="list")
def constraint_list() -> None:
    """List all constraints for this project."""
    list_typed_memories("constraint")


@constraint.command(name="search")
@click.argument("query")
def constraint_search(query: str) -> None:
    """Search constraints using full-text search."""
    search_typed_memories("constraint", query)


@constraint.command(name="get")
@click.argument("memory_id")
def constraint_get(memory_id: str) -> None:
    """Show full constraint detail."""
    get_and_print_typed_memory(memory_id)


@cli_root.cli.group()
def lesson() -> None:
    """Lessons: solved problems agents should not re-solve. Auto-surfaced at startup."""
    pass


@lesson.command(name="add")
@click.argument("title")
@click.option("--content", required=True, help="What the problem was and how it was solved")
@click.option("--tags", help="Comma-separated tags")
@click.option("--no-always-include", is_flag=True, default=False, help="Don't always include")
@click.option(
    "--scope",
    type=click.Choice(["project", "task"], case_sensitive=False),
    help="Override storage scope (project or task)",
)
@click.option(
    "--project",
    "project_scope",
    is_flag=True,
    default=False,
    help="Alias for --scope project",
)
@click.option("--level", help="Project level for project scope (L0, L1, L2, L3)")
@click.option("--task-id", help="Optional linked/origin task ID")
def lesson_add(
    title: str,
    content: str,
    tags: str | None,
    no_always_include: bool,
    scope: str | None,
    project_scope: bool,
    level: str | None,
    task_id: str | None,
) -> None:
    """Record a lesson learned (always shown at startup by default)."""
    resolved_scope = _resolve_typed_override_scope(
        scope=scope, project_scope=project_scope, level=level, command_name="lesson"
    )
    add_typed_memory(
        "lesson",
        title,
        content,
        tags,
        always_include=not no_always_include,
        scope=resolved_scope,
        level=level,
        task_id=task_id,
    )


@lesson.command(name="list")
def lesson_list() -> None:
    """List all lessons for this project."""
    list_typed_memories("lesson")


@lesson.command(name="search")
@click.argument("query")
def lesson_search(query: str) -> None:
    """Search lessons using full-text search."""
    search_typed_memories("lesson", query)


@lesson.command(name="get")
@click.argument("memory_id")
def lesson_get(memory_id: str) -> None:
    """Show full lesson detail."""
    get_and_print_typed_memory(memory_id)


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
    add_typed_memory("decision", title, content, tags, always_include=not no_always_include)


@decision.command(name="list")
def decision_list() -> None:
    """List all decisions for this project."""
    list_typed_memories("decision")


@decision.command(name="search")
@click.argument("query")
def decision_search(query: str) -> None:
    """Search decisions using full-text search."""
    search_typed_memories("decision", query)


@decision.command(name="get")
@click.argument("memory_id")
def decision_get(memory_id: str) -> None:
    """Show full decision detail."""
    get_and_print_typed_memory(memory_id)


@cli_root.cli.group()
def snippet() -> None:
    """Snippets: reusable commands, configs, and code patterns."""
    pass


@snippet.command(name="add")
@click.argument("title")
@click.option("--content", required=True, help="The reusable command or code")
@click.option("--tags", help="Comma-separated tags")
@click.option("--always-include", is_flag=True, default=False, help="Always include in context")
@click.option(
    "--scope",
    type=click.Choice(["project", "task"], case_sensitive=False),
    help="Override storage scope (project or task)",
)
@click.option(
    "--project",
    "project_scope",
    is_flag=True,
    default=False,
    help="Alias for --scope project",
)
@click.option("--level", help="Project level for project scope (L0, L1, L2, L3)")
@click.option("--task-id", help="Optional linked/origin task ID")
def snippet_add(
    title: str,
    content: str,
    tags: str | None,
    always_include: bool,
    scope: str | None,
    project_scope: bool,
    level: str | None,
    task_id: str | None,
) -> None:
    """Record a reusable command or code snippet (search on demand)."""
    resolved_scope = _resolve_typed_override_scope(
        scope=scope, project_scope=project_scope, level=level, command_name="snippet"
    )
    add_typed_memory(
        "snippet",
        title,
        content,
        tags,
        always_include=always_include,
        scope=resolved_scope,
        level=level,
        task_id=task_id,
    )


@snippet.command(name="list")
def snippet_list() -> None:
    """List all snippets for this project."""
    list_typed_memories("snippet")


@snippet.command(name="search")
@click.argument("query")
def snippet_search(query: str) -> None:
    """Search snippets using full-text search."""
    search_typed_memories("snippet", query)


@snippet.command(name="get")
@click.argument("memory_id")
def snippet_get(memory_id: str) -> None:
    """Show full snippet detail."""
    get_and_print_typed_memory(memory_id)
