"""Resource registration surface for future MCP phases."""

from __future__ import annotations

from typing import Any

import engram.services.context_service as context_service


def register_resources(server: Any) -> None:
    """Register MCP resources."""

    @server.resource("engram://startup")
    def get_startup() -> str:
        """Get engram startup context."""
        return context_service.get_startup_context_for_active_project()

    @server.resource("engram://task/{task_id}/context")
    def get_task_context(task_id: str) -> str:
        """Get engram task context."""
        return context_service.get_task_context_for_active_project(task_id)

    @server.resource("engram://snapshot")
    def get_snapshot() -> str:
        """Get engram snapshot context."""
        return context_service.get_snapshot_context_for_active_project()

    @server.resource("engram://handoff")
    def get_handoff() -> str:
        """Get engram handoff context."""
        return context_service.get_handoff_context_for_active_project()
