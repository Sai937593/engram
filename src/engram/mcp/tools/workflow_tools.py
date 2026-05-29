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
        """Get details of the currently active engram project."""
        try:
            project = engram.mcp.tools.resolve_active_project()
            slim_project = {
                "id": str(project["id"]),
                "name": str(project["name"]),
                "status": str(project["status"]),
            }
            return engram.mcp.tools._respond(
                {
                    "ok": True,
                    "project": slim_project,
                }
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_project_init(
        id: str,
        name: str,
        summary: str | None = None,
        repo_path: str | None = None,
    ) -> str:
        """Initialize a new project, bind it to a repository path, and set it as active."""
        try:
            project = engram.mcp.tools.init_project(
                id=id,
                name=name,
                summary=summary,
                repo_path=repo_path,
            )
            return engram.mcp.tools._respond(
                {
                    "ok": True,
                    "id": project["id"],
                    "name": project["name"],
                }
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_project_switch(project_id: str) -> str:
        """Switch the currently active project to the specified ID."""
        try:
            project = engram.mcp.tools.switch_project(project_id=project_id)
            return engram.mcp.tools._respond(
                {
                    "ok": True,
                    "id": project["id"],
                    "name": project["name"],
                }
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    async def engram_workflow_start() -> str:
        """Start or resume the next actionable task in the active engram project.

        This tool resolves the active project, checks out or creates the
        appropriate Git branch for the task, and returns the task details along with its branch,
        resumption status, and startup context (including relevant memories and files).
        This tool performs Git branch checkout and creation operations.
        """
        try:
            project = engram.mcp.tools.resolve_active_project()
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
        """Finish the active task: commit, push, and mark done in the active project.

        This tool stages all current changes, creates a conventional Git commit based on the active
        task and phase title, pushes to the remote repository, and marks the task as completed.
        If a pre-push test/hook fails, the push (and thus this tool) will block and fail.
        """
        try:
            project = engram.mcp.tools.resolve_active_project()
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
