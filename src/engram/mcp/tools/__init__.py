"""Subpackage entrypoint for MCP tools."""

from __future__ import annotations

from typing import Any

from engram.mcp.tools.common import _respond_error as _respond_error
from engram.mcp.tools.memory import register_memory_tools
from engram.mcp.tools.phase import register_phase_tools
from engram.mcp.tools.project import register_project_tools
from engram.mcp.tools.task import register_task_tools
from engram.mcp.tools.workflow import register_workflow_tools


def register_tools(server: Any) -> None:
    """Register all MCP tools."""
    register_project_tools(server)
    register_task_tools(server)
    register_phase_tools(server)
    register_memory_tools(server)
    register_workflow_tools(server)
