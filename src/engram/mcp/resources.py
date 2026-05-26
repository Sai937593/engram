"""Resource registration surface for future MCP phases."""

from __future__ import annotations

from typing import Any


def register_resources(server: Any) -> None:
    """Register MCP resources."""

    @server.resource("engram://startup")
    def get_startup() -> str:
        """Get engram startup context."""
        return "placeholder"

    @server.resource("engram://task/{task_id}/context")
    def get_task_context(task_id: str) -> str:
        """Get engram task context."""
        return f"placeholder: {task_id}"

    @server.resource("engram://snapshot")
    def get_snapshot() -> str:
        """Get engram snapshot context."""
        return "placeholder"

    @server.resource("engram://handoff")
    def get_handoff() -> str:
        """Get engram handoff context."""
        return "placeholder"
