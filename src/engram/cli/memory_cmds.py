"""Memory command group registration and compatibility exports."""

import importlib

import engram.cli as cli_root
from engram.cli.memory_cmds_common import VALID_MEMORY_FIELDS, VALID_MEMORY_TYPES


@cli_root.cli.group()
def memory() -> None:
    """Manage memories (freeform notes and snippets)."""
    pass


def _register_memory_commands() -> None:
    """Load memory subcommand modules so Click decorators register handlers."""
    importlib.import_module("engram.cli.memory_cmds_generic")
    importlib.import_module("engram.cli.memory_cmds_typed")


_register_memory_commands()

__all__ = ["VALID_MEMORY_FIELDS", "VALID_MEMORY_TYPES", "memory"]
