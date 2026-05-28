"""Tool registration surface for MCP phases."""

from __future__ import annotations

import functools
from typing import Any

import anyio.to_thread
import yaml

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


def _respond(data: dict[str, Any], keep_empty_keys: set[str] | None = None) -> str:
    """Recursively strip None values and empty lists/dicts, then serialize to YAML."""
    keys_to_keep = keep_empty_keys or set()

    def prune(val: Any, key: str | None = None) -> Any:
        if isinstance(val, dict):
            pruned_dict = {}
            for k, v in val.items():
                pruned_v = prune(v, k)
                if (
                    pruned_v is not None
                    and (pruned_v != [] or k in keys_to_keep)
                    and (pruned_v != {} or k in keys_to_keep)
                ):
                    pruned_dict[k] = pruned_v
            return pruned_dict
        elif isinstance(val, list):
            pruned_list = []
            for item in val:
                pruned_item = prune(item, None)
                if pruned_item is not None and pruned_item != [] and pruned_item != {}:
                    pruned_list.append(pruned_item)
            return pruned_list
        return val

    pruned_data = prune(data)
    return yaml.safe_dump(pruned_data, sort_keys=False)


def _respond_error(exc: EngramServiceError) -> str:
    """Format an EngramServiceError into a flat YAML error response."""
    known_fixes = {
        "DEPENDENCY_UNSATISFIED": "Complete all prerequisite tasks using engram_task_done before starting this task.",
        "NO_TASK_IN_PROGRESS": "Start a task first using engram_task_start.",
        "TASK_NOT_FOUND": "List tasks using engram_task_list to find the correct task ID or reference.",
        "TASK_AMBIGUOUS": "Use the exact 8-character task ID instead of the title. Run engram_task_list to find the task ID.",
        "DIRTY_WORKING_TREE": "Commit your changes using engram_workflow_finish or stash them before starting a new task.",
        "INVALID_TASK_STATUS": "Use a valid task status (todo, in-progress, done, blocked, or cancelled) and update using engram_task_update.",
        "PHASE_COMPLETION_BLOCKED": "Complete all unfinished tasks in the phase using engram_task_done, or update/cancel them using engram_task_update before completing the phase.",
        "UNFINISHED_TASKS": "Complete all unfinished tasks in the phase using engram_task_done, or update/cancel them using engram_task_update before completing the phase.",
    }

    fix_val = getattr(exc, "fix", None) or known_fixes.get(exc.code)

    resp_dict: dict[str, Any] = {
        "ok": False,
        "error": exc.code,
        "message": exc.message,
    }
    if fix_val:
        resp_dict["fix"] = fix_val

    return _respond(resp_dict)


def slim_task_dict(task: dict[str, Any]) -> dict[str, Any]:
    """Prune a full task dictionary to essential scan fields only."""
    return {
        "id": task["id"],
        "title": task["title"],
        "status": task["status"],
    }


def slim_phase_dict(phase: dict[str, Any]) -> dict[str, Any]:
    """Prune a full phase dictionary to essential scan fields only."""
    return {
        "id": phase["id"],
        "title": phase["title"],
        "status": phase["status"],
    }


def register_tools(server: Any) -> None:
    """Register MCP tools."""

    @server.tool()
    def engram_project_current() -> str:
        """Get details of the currently bound engram project."""
        try:
            project = resolve_current_project()
            slim_project = {
                "id": str(project["id"]),
                "name": str(project["name"]),
                "status": str(project["status"]),
            }
            return _respond(
                {
                    "ok": True,
                    "project": slim_project,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_task_list(status: str | None = None, phase: str | None = None) -> str:
        """List tasks for the currently bound engram project, optionally filtering by status or phase."""
        try:
            project = resolve_current_project()
            tasks = list_tasks(project_id=str(project["id"]), status=status, phase=phase)
            if not tasks:
                return _respond(
                    {
                        "ok": True,
                        "tasks": [],
                        "hint": f"No {status or 'todo'} tasks. Try status=all to see all tasks.",
                    },
                    keep_empty_keys={"tasks"},
                )
            return _respond(
                {
                    "ok": True,
                    "tasks": [slim_task_dict(t) for t in tasks],
                    "hint": "Use engram_task_get <id> for full task details",
                },
                keep_empty_keys={"tasks"},
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_task_get(task_ref: str) -> str:
        """Get a task by ID or task reference for the currently bound engram project."""
        try:
            project = resolve_current_project()
            task = get_task(project_id=str(project["id"]), task_ref=task_ref)
            return _respond(
                {
                    "ok": True,
                    "task": task,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_task_next() -> str:
        """Get the next actionable task for the currently bound engram project."""
        try:
            project = resolve_current_project()
            task = get_next_task(project_id=str(project["id"]))
            return _respond(
                {
                    "ok": True,
                    "task": task,
                }
            )
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
            return _respond(
                {
                    "ok": True,
                    "memories": memories,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_phase_list(status: str | None = None) -> str:
        """List phases for the currently bound engram project, optionally filtering by status."""
        try:
            project = resolve_current_project()
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
            project = resolve_current_project()
            project_id = str(project["id"])

            from engram.models.task import Task

            has_in_progress = any(
                t.status == "in-progress" for t in Task.list_by_project(project_id)
            )

            task = create_task(
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

            resp = {
                "ok": True,
                "id": task["id"],
                "title": task["title"],
            }
            if has_in_progress:
                resp["warn"] = (
                    "An in-progress task already exists in this project. Finish it before starting a new one."
                )

            return _respond(resp)
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_task_update(
        task_ref: str,
        updates: dict[str, Any],
    ) -> str:
        """Update an existing task in the currently bound engram project."""
        try:
            project = resolve_current_project()
            project_id = str(project["id"])

            from engram.models.task import Task
            from engram.services.task_service import VALID_TASK_UPDATE_FIELDS, resolve_task_ref

            task_id = resolve_task_ref(project_id, task_ref)
            task_before = Task.get(task_id)
            before_values = {}
            if task_before:
                for field in VALID_TASK_UPDATE_FIELDS:
                    val = getattr(task_before, field, None)
                    if isinstance(val, list):
                        before_values[field] = list(val)
                    else:
                        before_values[field] = val

            task = update_task(
                project_id=project_id,
                task_ref=task_ref,
                **updates,
            )

            updated_fields = []
            for field in VALID_TASK_UPDATE_FIELDS:
                after_val = task.get(field)
                before_val = before_values.get(field)
                if before_val != after_val:
                    updated_fields.append(field)

            return _respond(
                {
                    "ok": True,
                    "id": task["id"],
                    "updated_fields": sorted(updated_fields),
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_task_note_append(
        task_ref: str,
        note: str,
    ) -> str:
        """Append a note to a task's evidence log in the currently bound engram project."""
        try:
            project = resolve_current_project()
            task = append_task_note(
                project_id=str(project["id"]),
                task_ref=task_ref,
                note=note,
            )
            return _respond(
                {
                    "ok": True,
                    "id": task["id"],
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
            )
            return _respond(
                {
                    "ok": True,
                    "memory": memory,
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
    def engram_task_start(task_ref: str) -> str:
        """Start a task in the currently bound engram project, validating its dependencies."""
        try:
            project = resolve_current_project()
            task = start_task(
                project_id=str(project["id"]),
                task_ref=task_ref,
            )
            return _respond(
                {
                    "ok": True,
                    "id": task["id"],
                    "status": task["status"],
                    "next": "Run engram_memory_search with task keywords, then draft implementation_plan.md",
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    def engram_task_done(task_ref: str, evidence: str | None = None) -> str:
        """Complete a task in the currently bound engram project, optionally appending evidence."""
        try:
            project = resolve_current_project()
            task = complete_task(
                project_id=str(project["id"]),
                task_ref=task_ref,
                evidence=evidence,
            )
            # Determine phase_complete
            from engram.models.task import Task, get_effective_phase_title

            def local_is_same_phase(task_1: Task, task_2: Task) -> bool:
                if task_1.phase_id and task_2.phase_id:
                    return task_1.phase_id == task_2.phase_id
                return get_effective_phase_title(task_1) == get_effective_phase_title(task_2)

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

            return _respond(
                {
                    "ok": True,
                    "id": task["id"],
                    "status": task["status"],
                    "phase_complete": phase_complete,
                    "next": "Log lessons with engram_memory_create, then call engram_workflow_finish",
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    async def engram_workflow_start() -> str:
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
            res = await anyio.to_thread.run_sync(
                functools.partial(
                    start_workflow,
                    project_id=str(project["id"]),
                    repo_path=repo_paths[0],
                )
            )
            return res["context"]
        except EngramServiceError as exc:
            return _respond_error(exc)

    @server.tool()
    async def engram_workflow_finish(commit_type: str | None = None) -> str:
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
            res = await anyio.to_thread.run_sync(
                functools.partial(
                    finish_workflow,
                    project_id=str(project["id"]),
                    repo_path=repo_paths[0],
                    commit_type=commit_type,
                )
            )
            return _respond(
                {
                    "ok": True,
                    **res,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)
