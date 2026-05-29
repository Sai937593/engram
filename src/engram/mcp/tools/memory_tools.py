"""MCP tool registrations for memory search and creation."""

from __future__ import annotations

from typing import Any

from engram.mcp.tools.helpers import _respond, _respond_error
from engram.services.errors import EngramServiceError
from engram.services.memory_service import create_memory, search_memories
from engram.services.project_service import resolve_current_project


def register_memory_tools(server: Any) -> None:
    """Register memory search and creation tools on the server."""

    @server.tool()
    def engram_memory_search(
        query: str | None = None,
        type: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> str:
        """Search memories in the currently bound engram project."""
        try:
            project = resolve_current_project()
            memories = search_memories(
                project_id=str(project["id"]),
                query=query,
                type_filter=type,
                tags=tags,
                limit=limit,
            )
            if not memories:
                return _respond(
                    {
                        "ok": True,
                        "memories": [],
                        "hint": "No results. Try broader terms. Log key discoveries with engram_memory_create.",
                    },
                    keep_empty_keys={"memories"},
                )

            unique_types = sorted(list({m.get("type") for m in memories if m.get("type")}))
            type_plurals = []
            for t in unique_types:
                if t == "constraint":
                    type_plurals.append("constraints")
                elif t == "decision":
                    type_plurals.append("decisions")
                elif t == "snippet":
                    type_plurals.append("snippets")
                elif t == "lesson":
                    type_plurals.append("lessons")
                elif t == "note":
                    type_plurals.append("notes")
                elif t == "issue":
                    type_plurals.append("issues")
                else:
                    type_plurals.append(f"{t}s")

            type_wording = "/".join(type_plurals) if type_plurals else "constraints/decisions"
            hint = f"Apply these {type_wording} before drafting your implementation plan."

            return _respond(
                {
                    "ok": True,
                    "memories": memories,
                    "hint": hint,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_memory_create(
        type: str,
        title: str,
        content: str,
        scope: str = "project",
        task_id: str | None = None,
        tags: list[str] | None = None,
        always_include: bool = False,
        level: str | None = None,
        id: str | None = None,
        supersedes: str | None = None,
    ) -> str:
        """Create a new memory in the currently bound engram project."""
        try:
            project = resolve_current_project()
            memory = create_memory(
                project_id=str(project["id"]),
                type=type,
                title=title,
                content=content,
                scope=scope,
                task_id=task_id,
                tags=tags,
                always_include=always_include,
                level=level,
                id=id,
                supersedes=supersedes,
            )
            return _respond(
                {
                    "ok": True,
                    "id": memory["id"],
                    "type": memory["type"],
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)
