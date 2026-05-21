"""Engram CLI — Agentic persistent memory system."""

import os

import click
from rich.console import Console

from engram.db import init_db
from engram.models.project import Project

console = Console()

CONVENTIONAL_COMMIT_TYPES = {
    "feat",
    "fix",
    "docs",
    "chore",
    "refactor",
    "test",
    "ci",
    "style",
    "perf",
}


@click.group()
def cli():
    """Engram — Agentic persistent memory system."""
    init_db()


def get_current_project() -> Project:
    """Resolve the current project from the working directory."""
    cwd = os.getcwd()
    project = Project.find_by_repo_path(cwd)
    if not project:
        console.print("[red]Error:[/red] Current directory is not bound to any Engram project.")
        console.print("Run 'engram init' to register this repository.")
        raise SystemExit(1)
    return project


# Register all command groups — import order doesn't matter,
# each module calls cli.add_command / cli.group on import.
from engram.cli import context_cmds as _context_cmds  # noqa: E402, F401
from engram.cli import memory_cmds as _memory_cmds  # noqa: E402, F401
from engram.cli import project_cmds as _project_cmds  # noqa: E402, F401
from engram.cli import task_cmds as _task_cmds  # noqa: E402, F401
from engram.cli import ui_cmds as _ui_cmds  # noqa: E402, F401
from engram.cli import utils_cmds as _utils_cmds  # noqa: E402, F401
from engram.cli import work_cmds as _work_cmds  # noqa: E402, F401


def main():
    """Entry point for the ``engram`` console script."""
    cli()


if __name__ == "__main__":
    main()
