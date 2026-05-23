"""Task command group registration and compatibility exports."""

import importlib

import engram.cli as cli_root
from engram.cli.task_helpers import (
    VALID_TASK_FIELDS,
    VALID_TASK_PRIORITIES,
    VALID_TASK_STATUSES,
    check_dependency_cycle,
    get_effective_status,
    resolve_task_dependency,
)


@cli_root.cli.group()
def task() -> None:
    """Manage tasks."""
    pass


def _register_task_commands() -> None:
    """Load task subcommand modules so Click decorators register handlers."""
    importlib.import_module("engram.cli.task_cmds_lifecycle")
    importlib.import_module("engram.cli.task_cmds_mutation")
    importlib.import_module("engram.cli.task_cmds_query")


_register_task_commands()

__all__ = [
    "VALID_TASK_FIELDS",
    "VALID_TASK_PRIORITIES",
    "VALID_TASK_STATUSES",
    "check_dependency_cycle",
    "get_effective_status",
    "resolve_task_dependency",
    "task",
]
