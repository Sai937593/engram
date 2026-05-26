"""Tool registration surface for MCP phases."""

from __future__ import annotations

from typing import Any

from engram.services.project_service import resolve_current_project
from engram.services.task_service import list_tasks


def register_tools(server: Any) -> None:
    """Register MCP tools."""

    @server.tool()
    def engram_project_current() -> dict[str, Any]:
        """Get details of the currently bound engram project."""
        project = resolve_current_project()
        return {
            "ok": True,
            "project": project,
        }

    @server.tool()
    def engram_task_list(status: str | None = None, phase: str | None = None) -> dict[str, Any]:
        """List tasks for the currently bound engram project, optionally filtering by status or phase."""
        project = resolve_current_project()
        tasks = list_tasks(project_id=str(project["id"]), status=status, phase=phase)
        return {
            "ok": True,
            "tasks": tasks,
        }
