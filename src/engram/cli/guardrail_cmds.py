"""Guardrail command group and lifecycle operations."""

import click

import engram.cli as cli_root
from engram.cli.memory_cmds_common import resolve_memory_id_in_project
from engram.models.memory import Memory


@cli_root.cli.group()
def guardrail() -> None:
    """Manage project guardrail controls."""
    pass


@guardrail.command(name="demote")
@click.argument("memory_id")
@click.option("--reason", required=True, help="Required reason for this demotion.")
def guardrail_demote(memory_id: str, reason: str) -> None:
    """Demote a project guardrail memory by exactly one level."""
    project = cli_root.get_current_project()
    resolved_id = resolve_memory_id_in_project(memory_id, project.id)

    memory_item = Memory.get(resolved_id)
    if not memory_item:
        raise click.ClickException(f"Memory '{resolved_id}' not found in the current project.")

    try:
        previous_level, next_level = memory_item.demote_project_guardrail_level(reason)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    cli_root.console.print(
        f"[green]Guardrail '{memory_item.id}' demoted:[/green] {previous_level} -> {next_level}"
    )
