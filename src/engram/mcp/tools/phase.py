"""Phase registration surface for MCP."""

from __future__ import annotations

from typing import Any

import engram.services.project_service as project_service
from engram.mcp.tools.common import _respond, _respond_error, slim_phase_dict
from engram.services.errors import EngramServiceError
from engram.services.phase_service import complete_phase, list_phases, start_phase


def register_phase_tools(server: Any) -> None:
    """Register phase-scoped MCP tools."""

    @server.tool()
    def engram_phase_list(status: str | None = None) -> str:
        """List phases for the currently bound engram project, optionally filtering by status."""
        try:
            project = project_service.resolve_active_project()
            phases = list_phases(project_id=str(project["id"]), status=status)
            return _respond(
                {
                    "ok": True,
                    "phases": [slim_phase_dict(p) for p in phases],
                },
                keep_empty_keys={"phases"},
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_phase_start(phase_ref: str) -> str:
        """Start a phase in the currently bound engram project, demoting other active phases."""
        try:
            project = project_service.resolve_active_project()
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
            project = project_service.resolve_active_project()
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
