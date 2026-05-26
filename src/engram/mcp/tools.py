"""Tool registration surface for MCP phases."""

from __future__ import annotations

from typing import Any

from engram.services.memory_service import search_memories
from engram.services.phase_service import list_phases
from engram.services.project_service import resolve_current_project
from engram.services.task_service import get_next_task, get_task, list_tasks


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

    @server.tool()
    def engram_task_get(task_ref: str) -> dict[str, Any]:
        """Get a task by ID or task reference for the currently bound engram project."""
        project = resolve_current_project()
        task = get_task(project_id=str(project["id"]), task_ref=task_ref)
        return {
            "ok": True,
            "task": task,
        }

    @server.tool()
    def engram_task_next() -> dict[str, Any]:
        """Get the next actionable task for the currently bound engram project."""
        project = resolve_current_project()
        task = get_next_task(project_id=str(project["id"]))
        return {
            "ok": True,
            "task": task,
        }

    @server.tool()
    def engram_memory_search(
        query: str | None = None,
        type: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search memories in the currently bound engram project."""
        project = resolve_current_project()
        memories = search_memories(
            project_id=str(project["id"]),
            query=query,
            type_filter=type,
            tags=tags,
            limit=limit,
        )
        return {
            "ok": True,
            "memories": memories,
        }

    @server.tool()
    def engram_phase_list(status: str | None = None) -> dict[str, Any]:
        """List phases for the currently bound engram project, optionally filtering by status."""
        project = resolve_current_project()
        phases = list_phases(project_id=str(project["id"]), status=status)
        return {
            "ok": True,
            "phases": phases,
        }
