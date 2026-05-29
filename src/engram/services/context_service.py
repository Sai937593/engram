"""Context service read-only wrappers for current and active project flows."""

from __future__ import annotations

import engram.context as context
import engram.services.project_service as project_service
import engram.services.task as task_service


def _resolve_project_id_for_cwd(cwd: str | None = None) -> str:
    """Resolve the project ID bound to the provided or current repository path."""
    return str(project_service.resolve_current_project(cwd=cwd)["id"])


def _resolve_active_project_id() -> str:
    """Resolve the active project ID (no CWD fallback)."""
    return str(project_service.resolve_active_project()["id"])


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


def get_task_context_for_current_project(task_ref: str, cwd: str | None = None) -> str:
    """Return task context for a project-scoped task reference in the provided or current cwd."""
    project_id = _resolve_project_id_for_cwd(cwd=cwd)
    task_id = task_service.resolve_task_ref(project_id=project_id, task_ref=task_ref)
    return context.get_task_context(task_id)


def get_startup_context_for_active_project() -> str:
    """Return startup context for the active project."""
    project_id = _resolve_active_project_id()
    return context.get_startup_context(project_id)


def get_snapshot_context_for_active_project() -> str:
    """Return snapshot context for the active project."""
    project_id = _resolve_active_project_id()
    return context.get_snapshot_context(project_id)


def get_handoff_context_for_active_project() -> str:
    """Return handoff context for the active project."""
    project_id = _resolve_active_project_id()
    return context.get_handoff_context(project_id)


def get_task_context_for_active_project(task_ref: str) -> str:
    """Return task context for an active project-scoped task reference."""
    project_id = _resolve_active_project_id()
    task_id = task_service.resolve_task_ref(project_id=project_id, task_ref=task_ref)
    return context.get_task_context(task_id)
