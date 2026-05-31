"""Engram CLI - Agentic persistent memory system."""

import sys

if sys.platform.startswith("win"):
    for _stream in (sys.stdout, sys.stderr):
        if _stream is not None and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(errors="replace")
            except Exception:
                pass

import click
from rich.console import Console

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
    """Engram - Agentic persistent memory system."""


# Register all command groups - import order doesn't matter,
# each module calls cli.add_command / cli.group on import.
from engram.cli import project_cmds as _project_cmds  # noqa: E402, F401
from engram.cli import utils_cmds as _utils_cmds  # noqa: E402, F401


def main():
    """Entry point for the ``engram`` console script."""
    cli()


if __name__ == "__main__":
    main()
