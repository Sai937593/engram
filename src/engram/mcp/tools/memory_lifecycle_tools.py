"""MCP tool registrations for memory lifecycle operations."""

from __future__ import annotations

from typing import Any

from engram.mcp.tools.helpers import _respond, _respond_error
from engram.services.errors import EngramServiceError, ValidationError
from engram.services.memory_lifecycle_service import (
    archive_memory,
    delete_memory,
    demote_memory,
    supersede_memory,
)
from engram.services.memory_service import get_memory, update_memory
from engram.services.project_service import resolve_current_project


def _require_arg(name: str, value: Any) -> None:
    """Raise deterministic validation errors for missing required MCP arguments."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(
            code="VALIDATION_ERROR",
            message=f"Missing required argument: {name}.",
            details={"field": name},
        )


def register_memory_lifecycle_tools(server: Any) -> None:
    """Register memory lifecycle MCP tools on the server."""

    @server.tool()
    def engram_memory_get(memory_ref: str | None = None) -> str:
        try:
            project = resolve_current_project()
            _require_arg("memory_ref", memory_ref)
            memory_item = get_memory(project_id=str(project["id"]), memory_ref=memory_ref)
            return _respond({"ok": True, "memory": memory_item})
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_memory_update(
        memory_ref: str | None = None, updates: dict[str, Any] | None = None
    ) -> str:
        try:
            project = resolve_current_project()
            _require_arg("memory_ref", memory_ref)
            _require_arg("updates", updates)
            memory_item = update_memory(
                project_id=str(project["id"]),
                memory_ref=memory_ref,
                **updates,
            )
            return _respond({"ok": True, "memory": memory_item})
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_memory_supersede(
        memory_ref: str | None = None,
        title: str | None = None,
        content: str | None = None,
        type: str | None = None,
        scope: str | None = None,
        task_id: str | None = None,
        tags: list[str] | None = None,
        always_include: bool | None = None,
        level: str | None = None,
        id: str | None = None,
    ) -> str:
        try:
            project = resolve_current_project()
            _require_arg("memory_ref", memory_ref)
            _require_arg("title", title)
            _require_arg("content", content)
            memory_item = supersede_memory(
                project_id=str(project["id"]),
                memory_ref=memory_ref,
                title=title,
                content=content,
                type=type,
                scope=scope,
                task_id=task_id,
                tags=tags,
                always_include=always_include,
                level=level,
                id=id,
            )
            return _respond({"ok": True, "memory": memory_item})
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_memory_demote(memory_ref: str | None = None, reason: str | None = None) -> str:
        try:
            project = resolve_current_project()
            _require_arg("memory_ref", memory_ref)
            _require_arg("reason", reason)
            memory_item = demote_memory(
                project_id=str(project["id"]), memory_ref=memory_ref, reason=reason
            )
            return _respond({"ok": True, "memory": memory_item})
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_memory_archive(memory_ref: str | None = None) -> str:
        try:
            project = resolve_current_project()
            _require_arg("memory_ref", memory_ref)
            memory_item = archive_memory(project_id=str(project["id"]), memory_ref=memory_ref)
            return _respond({"ok": True, "memory": memory_item})
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_memory_delete(memory_ref: str | None = None, force: bool = False) -> str:
        try:
            project = resolve_current_project()
            _require_arg("memory_ref", memory_ref)
            deletion = delete_memory(
                project_id=str(project["id"]), memory_ref=memory_ref, force=force
            )
            return _respond({"ok": True, **deletion})
        except EngramServiceError as exc:
            return _respond_error(exc)
