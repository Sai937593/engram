"""MCP tool registrations for task CRUD and lifecycle."""

from __future__ import annotations

from typing import Any

import engram.mcp.tools
from engram.services.errors import EngramServiceError


def register_task_tools(server: Any) -> None:
    """Register task CRUD and lifecycle tools on the server."""

    @server.tool()
    def engram_task_list(status: str | None = None, phase: str | None = None) -> str:
        """List tasks for the currently bound engram project, optionally filtering by status or phase."""
        try:
            project = engram.mcp.tools.resolve_current_project()
            tasks = engram.mcp.tools.list_tasks(
                project_id=str(project["id"]), status=status, phase=phase
            )
            if not tasks:
                return engram.mcp.tools._respond(
                    {
                        "ok": True,
                        "tasks": [],
                        "hint": f"No {status or 'todo'} tasks. Try status=all to see all tasks.",
                    },
                    keep_empty_keys={"tasks"},
                )
            return engram.mcp.tools._respond(
                {
                    "ok": True,
                    "tasks": [engram.mcp.tools.slim_task_dict(t) for t in tasks],
                    "hint": "Use engram_task_get <id> for full task details",
                },
                keep_empty_keys={"tasks"},
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_task_get(task_ref: str) -> str:
        """Get a task by ID or task reference for the currently bound engram project."""
        try:
            project = engram.mcp.tools.resolve_current_project()
            task = engram.mcp.tools.get_task(project_id=str(project["id"]), task_ref=task_ref)
            return engram.mcp.tools._respond({"ok": True, "task": task})
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_task_next() -> str:
        """Get the next actionable task for the currently bound engram project."""
        try:
            project = engram.mcp.tools.resolve_current_project()
            task = engram.mcp.tools.get_next_task(project_id=str(project["id"]))
            return engram.mcp.tools._respond({"ok": True, "task": task})
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_task_create(
        title: str,
        description: str | None = None,
        status: str = "todo",
        priority: str = "medium",
        phase: str | None = None,
        phase_id: str | None = None,
        depends_on: str | None = None,
        acceptance: str | None = None,
        tags: list[str] | None = None,
        relevant_files: list[str] | None = None,
    ) -> str:
        """Create a new task in the currently bound engram project."""
        try:
            project = engram.mcp.tools.resolve_current_project()
            project_id = str(project["id"])
            from engram.models.task import Task

            has_in_progress = any(
                t.status == "in-progress" for t in Task.list_by_project(project_id)
            )
            task = engram.mcp.tools.create_task(
                project_id=project_id,
                title=title,
                description=description,
                status=status,
                priority=priority,
                phase=phase,
                phase_id=phase_id,
                depends_on=depends_on,
                acceptance=acceptance,
                tags=tags,
                relevant_files=relevant_files,
            )
            resp = {"ok": True, "id": task["id"], "title": task["title"]}
            if has_in_progress:
                resp["warn"] = (
                    "An in-progress task already exists in this project. Finish it before starting a new one."
                )
            return engram.mcp.tools._respond(resp)
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_task_update(task_ref: str, updates: dict[str, Any]) -> str:
        """Update an existing task in the currently bound engram project."""
        try:
            project = engram.mcp.tools.resolve_current_project()
            project_id = str(project["id"])
            from engram.models.task import Task
            from engram.services.task_service import VALID_TASK_UPDATE_FIELDS, resolve_task_ref

            task_id = resolve_task_ref(project_id, task_ref)
            task_before = Task.get(task_id)
            before_values = {}
            if task_before:
                for field in VALID_TASK_UPDATE_FIELDS:
                    val = getattr(task_before, field, None)
                    before_values[field] = list(val) if isinstance(val, list) else val
            task = engram.mcp.tools.update_task(project_id=project_id, task_ref=task_ref, **updates)
            updated_fields = [
                f for f in VALID_TASK_UPDATE_FIELDS if before_values.get(f) != task.get(f)
            ]
            return engram.mcp.tools._respond(
                {"ok": True, "id": task["id"], "updated_fields": sorted(updated_fields)}
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_task_note_append(task_ref: str, note: str) -> str:
        """Append a note to a task's evidence log in the currently bound engram project."""
        try:
            project = engram.mcp.tools.resolve_current_project()
            task = engram.mcp.tools.append_task_note(
                project_id=str(project["id"]), task_ref=task_ref, note=note
            )
            return engram.mcp.tools._respond({"ok": True, "id": task["id"]})
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_task_start(task_ref: str) -> str:
        """Start a task in the currently bound engram project, validating its dependencies."""
        try:
            project = engram.mcp.tools.resolve_current_project()
            task = engram.mcp.tools.start_task(project_id=str(project["id"]), task_ref=task_ref)
            return engram.mcp.tools._respond(
                {
                    "ok": True,
                    "id": task["id"],
                    "status": task["status"],
                    "next": "Run engram_memory_search with task keywords, then draft implementation_plan.md",
                }
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_task_done(task_ref: str, evidence: str | None = None) -> str:
        """Complete a task in the currently bound engram project, optionally appending evidence."""
        try:
            project = engram.mcp.tools.resolve_current_project()
            task = engram.mcp.tools.complete_task(
                project_id=str(project["id"]), task_ref=task_ref, evidence=evidence
            )
            from engram.models.task import Task, get_effective_phase_title

            def local_is_same_phase(t1: Task, t2: Task) -> bool:
                if t1.phase_id and t2.phase_id:
                    return t1.phase_id == t2.phase_id
                return get_effective_phase_title(t1) == get_effective_phase_title(t2)

            task_model = Task.get(task["id"])
            phase_complete = False
            if task_model:
                project_id = str(project["id"])
                tasks = Task.list_by_project(project_id)
                next_task = Task.get_next(project_id)
                if not next_task or not local_is_same_phase(next_task, task_model):
                    phase_tasks = [pt for pt in tasks if local_is_same_phase(pt, task_model)]
                    if all(pt.status in ("done", "cancelled") for pt in phase_tasks):
                        phase_complete = True
            return engram.mcp.tools._respond(
                {
                    "ok": True,
                    "id": task["id"],
                    "status": task["status"],
                    "phase_complete": phase_complete,
                    "next": "Log lessons with engram_memory_create, then call engram_workflow_finish",
                }
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)
