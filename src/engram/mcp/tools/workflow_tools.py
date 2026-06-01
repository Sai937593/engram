"""MCP tool registrations for workflow and project operations."""

from __future__ import annotations

import functools
from typing import Any

import anyio.to_thread

import engram.mcp.tools
from engram.mcp.tools.workflow_tool_helpers import (
    FINISH_GATE_ERROR_CODES,
    format_verification_finish_blocked,
)
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
        """Start or resume the next actionable task in the currently bound engram project."""
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
            if exc.code == "WORKFLOW_START_DRAFT_ONLY":
                from engram.services.workflow_formatter import format_start_blocked

                return format_start_blocked(
                    reason=exc.message,
                    next_guidance=(
                        "Complete minimum execution metadata on draft task(s), then set "
                        "status=open via engram_task_update and rerun engram_workflow_start. "
                        "If open-promotion fails, use TASK_METADATA_INCOMPLETE details to "
                        "fix missing/weak fields before retrying."
                    ),
                )
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    async def engram_workflow_finish(commit_type: str | None = None) -> str:
        """Finish the active task: commit, push, and mark done."""
        project_id: str | None = None
        try:
            project = engram.mcp.tools.resolve_current_project()
            project_id = str(project["id"])
            repo_paths = project.get("repo_paths", [])
            if not repo_paths:
                raise EngramServiceError(
                    code="PROJECT_NO_REPOS",
                    message="No repository paths configured for this project.",
                )
            res = await anyio.to_thread.run_sync(
                functools.partial(
                    engram.mcp.tools.finish_workflow,
                    project_id=project_id,
                    repo_path=repo_paths[0],
                    commit_type=commit_type,
                )
            )
            phase_complete = res["phase_complete"]
            next_guidance = (
                "Phase complete. Ask the user for permission to run the engram-phase-transition skill."
                if phase_complete
                else "Stop here. The active task is finished and committed. Await further instructions."
            )
            from engram.services.workflow_formatter import format_finish_success

            return format_finish_success(
                task_id=res["id"],
                commit_msg=res["commit"],
                phase_complete=phase_complete,
                next_guidance=next_guidance,
                task_title=res.get("task_title"),
                memory_review_outcome=res.get("memory_review_outcome"),
            )
        except EngramServiceError as exc:
            if exc.code in FINISH_GATE_ERROR_CODES and project_id:
                return format_verification_finish_blocked(
                    project_id=project_id, reason=exc.message, code=exc.code
                )
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    async def engram_workflow_verify() -> str:
        """Run repo-local workflow verification checks for the active task."""
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
                    engram.mcp.tools.verify_workflow,
                    project_id=str(project["id"]),
                    repo_path=repo_paths[0],
                )
            )
            from engram.services.workflow_formatter import format_verify_result

            next_guidance = (
                "Verification succeeded and staged changes are ready. Continue implementation or run engram_workflow_finish when ready."
                if res["passed"]
                else "Fix the first actionable target, then rerun engram_workflow_verify."
            )
            details = res["summary"] if res["passed"] else res.get("details", res["summary"])
            return format_verify_result(
                task_id=res["task_id"],
                task_title=res.get("task_title"),
                passed=bool(res["passed"]),
                details=details,
                next_guidance=next_guidance,
            )
        except EngramServiceError as exc:
            return engram.mcp.tools._respond_error(exc)

    @server.tool()
    def engram_project_init(
        name: str | None = None,
        project_id: str | None = None,
        summary: str | None = None,
    ) -> str:
        """Initialize a new engram project in the current workspace directory."""
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
