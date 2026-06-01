"""MCP tool registration for batch task creation."""

from __future__ import annotations

from typing import Any

import engram.mcp.tools
from engram.services.errors import EngramServiceError


def register_task_batch_tools(server: Any) -> None:
    """Register batch task creation MCP tools on the server."""

    @server.tool()
    def engram_task_create_many(tasks: list[dict[str, Any]] | None = None) -> str:
        """Create multiple tasks atomically in the currently bound engram project."""
        try:
            project = engram.mcp.tools.resolve_current_project()
            created = engram.mcp.tools.create_many_tasks(
                project_id=str(project["id"]), task_payloads=tasks or []
            )
            return engram.mcp.tools._respond(
                {
                    "ok": True,
                    "tasks": [{"id": t["id"], "title": t["title"]} for t in created],
                },
                keep_empty_keys={"tasks"},
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)
