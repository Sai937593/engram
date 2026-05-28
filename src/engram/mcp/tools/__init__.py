"""Modularized tool registrations for the Engram MCP server."""

from __future__ import annotations

from typing import Any

from engram.mcp.tools.helpers import (
    _respond,
    _respond_error,
    slim_phase_dict,
    slim_task_dict,
)
from engram.mcp.tools.memory_tools import register_memory_tools
from engram.mcp.tools.phase_tools import register_phase_tools
from engram.mcp.tools.task_tools import register_task_tools
from engram.mcp.tools.workflow_tools import register_workflow_tools
from engram.services.memory_service import create_memory, search_memories
from engram.services.phase_service import (
    complete_phase,
    create_phase,
    list_phases,
    start_phase,
)
from engram.services.project_service import resolve_current_project
from engram.services.task_service import (
    append_task_note,
    complete_task,
    create_task,
    get_next_task,
    get_task,
    list_tasks,
    start_task,
    update_task,
)
from engram.services.workflow_service import finish_workflow, start_workflow

__all__ = [
    "register_tools",
    "_respond",
    "_respond_error",
    "slim_phase_dict",
    "slim_task_dict",
    "register_memory_tools",
    "register_phase_tools",
    "register_task_tools",
    "register_workflow_tools",
    "create_memory",
    "search_memories",
    "complete_phase",
    "create_phase",
    "list_phases",
    "start_phase",
    "resolve_current_project",
    "append_task_note",
    "complete_task",
    "create_task",
    "get_next_task",
    "get_task",
    "list_tasks",
    "start_task",
    "update_task",
    "finish_workflow",
    "start_workflow",
]


def register_tools(server: Any) -> None:
    """Register all modular MCP tools on the server."""
    register_task_tools(server)
    register_memory_tools(server)
    register_phase_tools(server)
    register_workflow_tools(server)
