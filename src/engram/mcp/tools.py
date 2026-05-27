"""Tool registration surface for MCP phases."""

from __future__ import annotations

from typing import Any

from engram.services.errors import EngramServiceError
from engram.services.memory_service import create_memory, search_memories
from engram.services.phase_service import complete_phase, list_phases, start_phase
from engram.services.project_service import resolve_current_project
from engram.services.task_service import (
    append_task_note,
    complete_task,
    create_task,
    get_next_task,
    get_task,
    list_tasks,
    start_task,
    update_task,
)
from engram.services.workflow_service import finish_workflow, start_workflow


def register_tools(server: Any) -> None:
    """Register MCP tools."""

    @server.tool()
    def engram_project_current() -> dict[str, Any]:
        """Get details of the currently bound engram project."""
        try:
            project = resolve_current_project()
            return {
                "ok": True,
                "project": project,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

    @server.tool()
    def engram_task_list(status: str | None = None, phase: str | None = None) -> dict[str, Any]:
        """List tasks for the currently bound engram project, optionally filtering by status or phase."""
        try:
            project = resolve_current_project()
            tasks = list_tasks(project_id=str(project["id"]), status=status, phase=phase)
            return {
                "ok": True,
                "tasks": tasks,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

    @server.tool()
    def engram_task_get(task_ref: str) -> dict[str, Any]:
        """Get a task by ID or task reference for the currently bound engram project."""
        try:
            project = resolve_current_project()
            task = get_task(project_id=str(project["id"]), task_ref=task_ref)
            return {
                "ok": True,
                "task": task,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

    @server.tool()
    def engram_task_next() -> dict[str, Any]:
        """Get the next actionable task for the currently bound engram project."""
        try:
            project = resolve_current_project()
            task = get_next_task(project_id=str(project["id"]))
            return {
                "ok": True,
                "task": task,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

    @server.tool()
    def engram_memory_search(
        query: str | None = None,
        type: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
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
            return {
                "ok": True,
                "memories": memories,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

    @server.tool()
    def engram_phase_list(status: str | None = None) -> dict[str, Any]:
        """List phases for the currently bound engram project, optionally filtering by status."""
        try:
            project = resolve_current_project()
            phases = list_phases(project_id=str(project["id"]), status=status)
            return {
                "ok": True,
                "phases": phases,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

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
    ) -> dict[str, Any]:
        """Create a new task in the currently bound engram project."""
        try:
            project = resolve_current_project()
            task = create_task(
                project_id=str(project["id"]),
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
            return {
                "ok": True,
                "task": task,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

    @server.tool()
    def engram_task_update(
        task_ref: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing task in the currently bound engram project."""
        try:
            project = resolve_current_project()
            task = update_task(
                project_id=str(project["id"]),
                task_ref=task_ref,
                **updates,
            )
            return {
                "ok": True,
                "task": task,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

    @server.tool()
    def engram_task_note_append(
        task_ref: str,
        note: str,
    ) -> dict[str, Any]:
        """Append a note to a task's evidence log in the currently bound engram project."""
        try:
            project = resolve_current_project()
            task = append_task_note(
                project_id=str(project["id"]),
                task_ref=task_ref,
                note=note,
            )
            return {
                "ok": True,
                "task": task,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

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
    ) -> dict[str, Any]:
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
            )
            return {
                "ok": True,
                "memory": memory,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

    @server.tool()
    def engram_phase_start(phase_ref: str) -> dict[str, Any]:
        """Start a phase in the currently bound engram project, demoting other active phases."""
        try:
            project = resolve_current_project()
            phase = start_phase(
                project_id=str(project["id"]),
                phase_ref=phase_ref,
            )
            return {
                "ok": True,
                "phase": phase,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

    @server.tool()
    def engram_phase_complete(phase_ref: str) -> dict[str, Any]:
        """Complete a phase in the currently bound engram project, validating no unfinished tasks remain."""
        try:
            project = resolve_current_project()
            phase = complete_phase(
                project_id=str(project["id"]),
                phase_ref=phase_ref,
            )
            return {
                "ok": True,
                "phase": phase,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

    @server.tool()
    def engram_task_start(task_ref: str) -> dict[str, Any]:
        """Start a task in the currently bound engram project, validating its dependencies."""
        try:
            project = resolve_current_project()
            task = start_task(
                project_id=str(project["id"]),
                task_ref=task_ref,
            )
            return {
                "ok": True,
                "task": task,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

    @server.tool()
    def engram_task_done(task_ref: str, evidence: str | None = None) -> dict[str, Any]:
        """Complete a task in the currently bound engram project, optionally appending evidence."""
        try:
            project = resolve_current_project()
            task = complete_task(
                project_id=str(project["id"]),
                task_ref=task_ref,
                evidence=evidence,
            )
            return {
                "ok": True,
                "task": task,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

    @server.tool()
    def engram_workflow_start() -> dict[str, Any]:
        """Start or resume the next actionable task in the currently bound engram project.

        This tool resolves the project bound to the current directory, checks out or creates the
        appropriate Git branch for the task, and returns the task details along with its branch,
        resumption status, and startup context (including relevant memories and files).
        This tool performs Git branch checkout and creation operations.
        """
        try:
            project = resolve_current_project()
            repo_paths = project.get("repo_paths", [])
            if not repo_paths:
                raise EngramServiceError(
                    code="PROJECT_NO_REPOS",
                    message="No repository paths configured for this project.",
                )
            res = start_workflow(project_id=str(project["id"]), repo_path=repo_paths[0])
            return {
                "ok": True,
                **res,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }

    @server.tool()
    def engram_workflow_finish(commit_type: str | None = None) -> dict[str, Any]:
        """Finish the active task: commit, push, and mark done.

        This tool stages all current changes, creates a conventional Git commit based on the active
        task and phase title, pushes to the remote repository, and marks the task as completed.
        If a pre-push test/hook fails, the push (and thus this tool) will block and fail.
        """
        try:
            project = resolve_current_project()
            repo_paths = project.get("repo_paths", [])
            if not repo_paths:
                raise EngramServiceError(
                    code="PROJECT_NO_REPOS",
                    message="No repository paths configured for this project.",
                )
            res = finish_workflow(
                project_id=str(project["id"]),
                repo_path=repo_paths[0],
                commit_type=commit_type,
            )
            return {
                "ok": True,
                **res,
            }
        except EngramServiceError as exc:
            return {
                "ok": False,
                "error": exc.to_dict(),
            }
