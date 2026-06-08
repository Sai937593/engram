"""MCP tool registrations for plan operations."""

from __future__ import annotations

from typing import Any

from engram.mcp.tools.helpers import _respond, _respond_error, build_list_payload
from engram.services.errors import EngramServiceError
from engram.services.plan_service import (
    activate_plan,
    create_plan,
    get_current_plan,
    get_plan,
    list_plans,
    update_plan,
)
from engram.services.project_service import resolve_current_project


def register_plan_tools(server: Any) -> None:
    """Register plan-related tools on the MCP server."""

    @server.tool()
    def engram_plan_current() -> str:
        """Show the active plan for the currently bound project."""
        try:
            project = resolve_current_project()
            plan = get_current_plan(project_id=str(project["id"]))
            return _respond(
                {
                    "ok": True,
                    "plan": plan,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_plan_create(
        title: str,
        slug: str | None = None,
        status: str = "draft",
        source_doc_path: str | None = None,
        key: str | None = None,
        activate: bool = False,
    ) -> str:
        """Register a new plan in the currently bound project."""
        try:
            project = resolve_current_project()
            plan = create_plan(
                project_id=str(project["id"]),
                title=title,
                slug=slug,
                status=status,
                source_doc_path=source_doc_path,
                key=key,
                activate=activate,
            )
            return _respond(
                {
                    "ok": True,
                    "plan": plan,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_plan_activate(plan_ref: str) -> str:
        """Activate a plan in the currently bound project, enforcing exactly one active plan."""
        try:
            project = resolve_current_project()
            plan = activate_plan(
                project_id=str(project["id"]),
                plan_ref=plan_ref,
            )
            return _respond(
                {
                    "ok": True,
                    "plan": plan,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_plan_update(
        plan_ref: str,
        title: str | None = None,
        slug: str | None = None,
        status: str | None = None,
        source_doc_path: str | None = None,
    ) -> str:
        """Update metadata/status/source doc for a plan in the currently bound project."""
        try:
            project = resolve_current_project()
            plan = update_plan(
                project_id=str(project["id"]),
                plan_ref=plan_ref,
                title=title,
                slug=slug,
                status=status,
                source_doc_path=source_doc_path,
            )
            return _respond(
                {
                    "ok": True,
                    "plan": plan,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_plan_list(status: str | None = None) -> str:
        """List plans for the currently bound project, optionally filtering by status."""
        try:
            project = resolve_current_project()
            plans = list_plans(project_id=str(project["id"]), status=status)

            filters = {"status": "all" if status is None else status.strip().casefold()}
            payload = build_list_payload(
                filters=filters,
                items=plans,
                populated_next_action="Use engram_plan_get <plan_ref> for full plan details.",
                empty_next_action="Create your first plan with engram_plan_create.",
            )
            return _respond(payload, keep_empty_keys={"items"})
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_plan_get(plan_ref: str) -> str:
        """Show full plan detail for a given plan ID or key in the currently bound project."""
        try:
            project = resolve_current_project()
            plan = get_plan(
                project_id=str(project["id"]),
                plan_ref=plan_ref,
            )
            return _respond(
                {
                    "ok": True,
                    "plan": plan,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)
