"""Workflow registration surface for MCP."""

from __future__ import annotations

import functools
from typing import Any

import anyio.to_thread

import engram.services.project_service as project_service
from engram.mcp.tools.common import _respond, _respond_error
from engram.services.errors import EngramServiceError
from engram.services.workflow_service import finish_workflow, start_workflow


def register_workflow_tools(server: Any) -> None:
    """Register workflow-scoped MCP tools."""

    @server.tool()
    async def engram_workflow_start() -> str:
        """Start or resume the next actionable task in the currently bound engram project.

        This tool resolves the project bound to the current directory, checks out or creates the
        appropriate Git branch for the task, and returns the task details along with its branch,
        resumption status, and startup context (including relevant memories and files).
        This tool performs Git branch checkout and creation operations.
        """
        try:
            project = project_service.resolve_active_project()
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
            project = project_service.resolve_active_project()
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
            phase_complete = res["phase_complete"]
            next_guidance = (
                "Phase complete. Ask the user for permission to run the engram-phase-transition skill."
                if phase_complete
                else "Run engram_workflow_start to claim the next task."
            )
            return _respond(
                {
                    "ok": True,
                    "id": res["id"],
                    "commit": res["commit"],
                    "phase_complete": phase_complete,
                    "next": next_guidance,
                }
            )
        except EngramServiceError as exc:
            return _respond_error(exc)
