"""Project registration surface for MCP."""

from __future__ import annotations

from typing import Any

import engram.services.project_service as project_service
from engram.mcp.tools.common import _respond, _respond_error
from engram.services.errors import EngramServiceError


def register_project_tools(server: Any) -> None:
    """Register project-scoped MCP tools."""

    @server.tool()
    def engram_project_current() -> str:
        """Get details of the currently bound engram project."""
        try:
            project = project_service.resolve_active_project()
            slim_project = {
                "id": str(project["id"]),
                "name": str(project["name"]),
                "status": str(project["status"]),
            }
            return _respond(
                {
                    "ok": True,
                    "project": slim_project,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_project_init(
        name: str,
        id: str | None = None,
        summary: str | None = None,
        repo_paths: list[str] | None = None,
    ) -> str:
        """Initialize a new engram project and bind repo paths to it, setting it active."""
        try:
            project = project_service.init_project(
                id=id, name=name, summary=summary, repo_paths=repo_paths
            )
            slim_project = {
                "id": str(project["id"]),
                "name": str(project["name"]),
                "status": str(project["status"]),
            }
            return _respond(
                {
                    "ok": True,
                    "project": slim_project,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_project_switch(id: str) -> str:
        """Switch the active engram project."""
        try:
            project = project_service.switch_project(id=id)
            slim_project = {
                "id": str(project["id"]),
                "name": str(project["name"]),
                "status": str(project["status"]),
            }
            return _respond(
                {
                    "ok": True,
                    "project": slim_project,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)
