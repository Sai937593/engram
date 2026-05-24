"""Phase command group registration and compatibility exports."""

import importlib

import engram.cli as cli_root
from engram.cli.phase_cmds_common import VALID_PHASE_FIELDS, VALID_PHASE_STATUSES


@cli_root.cli.group()
def phase() -> None:
    """Manage phases."""
    pass


def _register_phase_commands() -> None:
    """Load phase subcommand modules so Click decorators register handlers."""
    importlib.import_module("engram.cli.phase_cmds_query")
    importlib.import_module("engram.cli.phase_cmds_lifecycle")


_register_phase_commands()

__all__ = [
    "VALID_PHASE_FIELDS",
    "VALID_PHASE_STATUSES",
    "phase",
]
