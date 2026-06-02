"""MCP tool registrations for phase operations."""

from __future__ import annotations

from typing import Any

from engram.mcp.tools.helpers import _respond, _respond_error, build_list_payload
from engram.services.errors import EngramServiceError
from engram.services.phase_service import (
    archive_phase,
    cancel_phase,
    complete_phase,
    create_phase,
    list_phases,
    start_phase,
    update_phase,
)
from engram.services.project_service import resolve_current_project


def _phase_list_filters(status: str | None, view: str) -> dict[str, str]:
    """Resolve the compact phase-list filter echo."""
    return {
        "status": "all" if status is None else status.strip().casefold(),
        "view": view.strip().casefold(),
    }


def register_phase_tools(server: Any) -> None:
    """Register phase-related tools on the server."""

    @server.tool()
    def engram_phase_list(status: str | None = None, view: str = "compact") -> str:
        """List phases for the currently bound engram project, optionally filtering by status."""
        try:
            project = resolve_current_project()
            phases = list_phases(project_id=str(project["id"]), status=status, view=view)
            payload = build_list_payload(
                filters=_phase_list_filters(status, view),
                items=phases,
                populated_next_action="Use engram_phase_start <id> to activate a phase.",
                empty_next_action="Create the first phase with engram_phase_create.",
            )
            return _respond(payload, keep_empty_keys={"items"})
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_phase_create(
        title: str,
        description: str | None = None,
        status: str = "planned",
        acceptance: str | None = None,
        key: str | None = None,
    ) -> str:
        """Create a new phase in the currently bound engram project."""
        try:
            project = resolve_current_project()
            phase = create_phase(
                project_id=str(project["id"]),
                title=title,
                description=description,
                status=status,
                acceptance=acceptance,
                key=key,
            )
            return _respond(
                {
                    "ok": True,
                    "id": phase["id"],
                    "title": phase["title"],
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_phase_start(phase_ref: str) -> str:
        """Start a phase in the currently bound engram project, demoting other active phases."""
        try:
            project = resolve_current_project()
            phase = start_phase(
                project_id=str(project["id"]),
                phase_ref=phase_ref,
            )
            return _respond(
                {
                    "ok": True,
                    "phase": phase,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_phase_complete(phase_ref: str) -> str:
        """Complete a phase in the currently bound engram project, validating no unfinished tasks remain."""
        try:
            project = resolve_current_project()
            phase = complete_phase(
                project_id=str(project["id"]),
                phase_ref=phase_ref,
            )
            return _respond(
                {
                    "ok": True,
                    "phase": phase,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_phase_update(
        phase_ref: str,
        title: str | None = None,
        description: str | None = None,
        acceptance: str | None = None,
        evidence: str | None = None,
    ) -> str:
        """Update mutable phase metadata fields in the currently bound engram project."""
        try:
            project = resolve_current_project()
            phase = update_phase(
                project_id=str(project["id"]),
                phase_ref=phase_ref,
                title=title,
                description=description,
                acceptance=acceptance,
                evidence=evidence,
            )
            return _respond(
                {
                    "ok": True,
                    "phase": phase,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_phase_cancel(phase_ref: str, reason: str | None = None) -> str:
        """Cancel a phase after validating lifecycle safety rules."""
        try:
            project = resolve_current_project()
            phase = cancel_phase(
                project_id=str(project["id"]),
                phase_ref=phase_ref,
                reason=reason,
            )
            return _respond(
                {
                    "ok": True,
                    "phase": phase,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_phase_archive(phase_ref: str) -> str:
        """Archive a terminal phase after validating lifecycle safety rules."""
        try:
            project = resolve_current_project()
            result = archive_phase(
                project_id=str(project["id"]),
                phase_ref=phase_ref,
            )
            return _respond(
                {
                    "ok": True,
                    **result,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)
