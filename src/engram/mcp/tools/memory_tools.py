"""MCP tool registrations for memory search and creation."""

from __future__ import annotations

from typing import Any

from engram.mcp.tools.helpers import _respond, _respond_error, build_list_payload
from engram.services.errors import EngramServiceError
from engram.services.memory_service import create_memory, list_memories, search_memories
from engram.services.project_service import resolve_current_project


def _memory_search_markdown(memories: list[dict[str, Any]]) -> str:
    """Build a compact markdown summary for memory search results."""
    if not memories:
        return (
            "## Memory Search\n"
            "No matching memories found.\n\n"
            "Next: broaden terms and capture new findings with `engram_memory_create`."
        )
    lines = ["## Memory Search", f"Matches: {len(memories)}"]
    for memory_item in memories[:5]:
        mem_id = str(memory_item.get("id", ""))
        mem_type = str(memory_item.get("type", "memory"))
        title = str(memory_item.get("title", "")).strip() or "Untitled"
        lines.append(f"- `{mem_id}` [{mem_type}] {title}")
    if len(memories) > 5:
        lines.append(f"- ... {len(memories) - 5} more")
    lines.append("")
    lines.append("Next: apply relevant memories before implementation.")
    return "\n".join(lines)


def _memory_list_filters(
    query: str | None,
    type: str | None,
    limit: int,
    view: str,
    include_superseded: bool,
) -> dict[str, Any]:
    """Resolve the compact memory-list filter echo."""
    return {
        "query": query,
        "type": type,
        "limit": limit,
        "view": view.strip().casefold(),
        "include_superseded": include_superseded,
    }


def register_memory_tools(server: Any) -> None:
    """Register memory search and creation tools on the server."""

    @server.tool()
    def engram_memory_list(
        query: str | None = None,
        limit: int = 50,
        view: str = "compact",
        include_superseded: bool = False,
        type: str | None = None,
    ) -> str:
        """List project-scoped memories with compact default output and optional query filtering."""
        try:
            project = resolve_current_project()
            memories = list_memories(
                project_id=str(project["id"]),
                type_filter=type,
                query=query,
                limit=limit,
                include_superseded=include_superseded,
                view=view,
            )
            payload = build_list_payload(
                filters=_memory_list_filters(query, type, limit, view, include_superseded),
                items=memories,
                populated_next_action="Use engram_memory_get <id> for full memory details.",
                empty_next_action="Try query=<term> or view=detail to broaden the list.",
            )
            return _respond(payload, keep_empty_keys={"items"})
        except EngramServiceError as exc:
            return _respond_error(exc)

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
                        "result": _memory_search_markdown([]),
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
                    "result": _memory_search_markdown(memories),
                    "hint": hint,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_memory_create(
        content: str,
        title: str | None = None,
        type: str = "note",
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
                content=content,
                type=type,
                title=title,
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
