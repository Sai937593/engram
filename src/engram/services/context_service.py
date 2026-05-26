"""Context service read-only wrappers for current project flows."""

from __future__ import annotations

import engram.context as context
from engram.services import project_service


def _resolve_project_id_for_cwd(cwd: str | None = None) -> str:
    """Resolve the project ID bound to the provided or current repository path."""
    return str(project_service.resolve_current_project(cwd=cwd)["id"])


def get_startup_context_for_current_project(cwd: str | None = None) -> str:
    """Return startup context for the project bound to the provided or current cwd."""
    project_id = _resolve_project_id_for_cwd(cwd=cwd)
    return context.get_startup_context(project_id)


def get_snapshot_context_for_current_project(cwd: str | None = None) -> str:
    """Return snapshot context for the project bound to the provided or current cwd."""
    project_id = _resolve_project_id_for_cwd(cwd=cwd)
    return context.get_snapshot_context(project_id)


def get_handoff_context_for_current_project(cwd: str | None = None) -> str:
    """Return handoff context for the project bound to the provided or current cwd."""
    project_id = _resolve_project_id_for_cwd(cwd=cwd)
    return context.get_handoff_context(project_id)
