"""MCP tool registrations for task maintenance lifecycle operations."""

from __future__ import annotations

from typing import Any

import engram.mcp.tools
from engram.services.errors import EngramServiceError


def register_task_maintenance_tools(server: Any) -> None:
    """Register task maintenance lifecycle tools on the server."""

    @server.tool()
    def engram_task_block(task_ref: str, reason: str | None = None) -> str:
        """Block a task in the currently bound engram project."""
        try:
            project = engram.mcp.tools.resolve_current_project()
            task = engram.mcp.tools.block_task(
                project_id=str(project["id"]), task_ref=task_ref, reason=reason
            )
            return engram.mcp.tools._respond(
                {"ok": True, "id": task["id"], "status": task["status"]}
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_task_unblock(
        task_ref: str,
        target_status: str = "todo",
        note: str | None = None,
    ) -> str:
        """Unblock a task back to a planned status in the currently bound engram project."""
        try:
            project = engram.mcp.tools.resolve_current_project()
            task = engram.mcp.tools.unblock_task(
                project_id=str(project["id"]),
                task_ref=task_ref,
                target_status=target_status,
                note=note,
            )
            return engram.mcp.tools._respond(
                {"ok": True, "id": task["id"], "status": task["status"]}
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_task_cancel(task_ref: str, reason: str | None = None) -> str:
        """Cancel a task in the currently bound engram project."""
        try:
            project = engram.mcp.tools.resolve_current_project()
            task = engram.mcp.tools.cancel_task(
                project_id=str(project["id"]), task_ref=task_ref, reason=reason
            )
            return engram.mcp.tools._respond(
                {"ok": True, "id": task["id"], "status": task["status"]}
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_task_retire(task_ref: str, reason: str | None = None) -> str:
        """Retire a task by deleting it after terminal completion/cancellation."""
        try:
            project = engram.mcp.tools.resolve_current_project()
            result = engram.mcp.tools.retire_task(
                project_id=str(project["id"]), task_ref=task_ref, reason=reason
            )
            task = result["task"]
            return engram.mcp.tools._respond(
                {
                    "ok": True,
                    "deleted": result["deleted"],
                    "id": task["id"],
                    "status": task["status"],
                }
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)
