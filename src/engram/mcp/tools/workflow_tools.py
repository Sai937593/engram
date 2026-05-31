"""MCP tool registrations for workflow and project operations."""

from __future__ import annotations

import functools
from typing import Any

import anyio.to_thread

import engram.mcp.tools
from engram.services.errors import EngramServiceError


def register_workflow_tools(server: Any) -> None:
    """Register workflow and project tools on the server."""

    @server.tool()
    def engram_project_current() -> str:
        """Get details of the currently bound engram project."""
        try:
            status = engram.mcp.tools.get_current_project_status()
            response: dict[str, Any] = {
                "ok": True,
                "initialized": bool(status["initialized"]),
                "status": str(status["status"]),
            }
            if status.get("repo_root"):
                response["repo_root"] = str(status["repo_root"])
            if status.get("db_path"):
                response["db_path"] = str(status["db_path"])
            if "db_exists" in status:
                response["db_exists"] = bool(status["db_exists"])
            if status.get("next_action"):
                response["next"] = str(status["next_action"])
            if status.get("project"):
                project = status["project"]
                response["project"] = {
                    "id": str(project["id"]),
                    "name": str(project["name"]),
                    "status": str(project["status"]),
                }
            return engram.mcp.tools._respond(response)
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    async def engram_workflow_start() -> str:
        """Start or resume the next actionable task in the currently bound engram project.

        This tool resolves the project bound to the current directory, checks out or creates the
        appropriate Git branch for the task, and returns the task details along with its branch,
        resumption status, and startup context (including relevant memories and files).
        This tool performs Git branch checkout and creation operations.
        """
        try:
            project = engram.mcp.tools.resolve_current_project()
            repo_paths = project.get("repo_paths", [])
            if not repo_paths:
                raise EngramServiceError(
                    code="PROJECT_NO_REPOS",
                    message="No repository paths configured for this project.",
                )
            res = await anyio.to_thread.run_sync(
                functools.partial(
                    engram.mcp.tools.start_workflow,
                    project_id=str(project["id"]),
                    repo_path=repo_paths[0],
                )
            )
            return res["context"]
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    async def engram_workflow_finish(commit_type: str | None = None) -> str:
        """Finish the active task: commit, push, and mark done.

        This tool stages all current changes, creates a conventional Git commit based on the active
        task and phase title, pushes to the remote repository, and marks the task as completed.
        If a pre-push test/hook fails, the push (and thus this tool) will block and fail.
        """
        try:
            project = engram.mcp.tools.resolve_current_project()
            repo_paths = project.get("repo_paths", [])
            if not repo_paths:
                raise EngramServiceError(
                    code="PROJECT_NO_REPOS",
                    message="No repository paths configured for this project.",
                )
            res = await anyio.to_thread.run_sync(
                functools.partial(
                    engram.mcp.tools.finish_workflow,
                    project_id=str(project["id"]),
                    repo_path=repo_paths[0],
                    commit_type=commit_type,
                )
            )
            phase_complete = res["phase_complete"]
            next_guidance = (
                "Phase complete. Ask the user for permission to run the engram-phase-transition skill."
                if phase_complete
                else "Run engram_workflow_start to claim the next task."
            )
            return engram.mcp.tools._respond(
                {
                    "ok": True,
                    "id": res["id"],
                    "commit": res["commit"],
                    "phase_complete": phase_complete,
                    "next": next_guidance,
                }
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_project_init(
        name: str | None = None,
        project_id: str | None = None,
        summary: str | None = None,
    ) -> str:
        """Initialize a new engram project in the current workspace directory.

        Creates the repo-local database inside `.engram/`, writes project metadata, and ensures
        `.engram/` is added to the repository `.gitignore`.
        """
        try:
            project = engram.mcp.tools.initialize_project(
                name=name, project_id=project_id, summary=summary
            )
            slim_project = {
                "id": str(project["id"]),
                "name": str(project["name"]),
                "status": str(project["status"]),
            }
            return engram.mcp.tools._respond(
                {
                    "ok": True,
                    "created": bool(project.get("created")),
                    "project": slim_project,
                    "hint": "Project successfully bound. Run engram_workflow_start or engram_task_list to start.",
                }
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_project_diagnostics() -> str:
        """Inspect repo root, DB health/schema, and .gitignore state for the current workspace."""
        try:
            diagnostics = engram.mcp.tools.get_project_diagnostics()
            return engram.mcp.tools._respond({"ok": True, **diagnostics})
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)
