"""Tool registration surface for MCP phases."""

from __future__ import annotations

from typing import Any

from engram.services.project_service import resolve_current_project


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
