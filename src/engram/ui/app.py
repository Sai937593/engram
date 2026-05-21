"""FastAPI app factory for the read-only local inspection UI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from engram.ui import read_model
from engram.ui import state as ui_state

UI_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(UI_DIR / "templates"))


def create_app(state_path: Path | None = None) -> FastAPI:
    """Create the read-only Engram UI app for the latest launched project."""
    app = FastAPI(title="Engram UI", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(UI_DIR / "static")), name="static")

    def active_target() -> ui_state.UiTarget:
        try:
            return ui_state.require_target(state_path)
        except ui_state.UiStateError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    def base_context(request: Request, active: str) -> dict:
        target = active_target()
        project = read_model.get_project(target.project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return {
            "request": request,
            "project": project,
            "ui_target": target,
            "active": active,
            "snapshot_version": _combined_snapshot_version(target),
            "last_synced": datetime.now().strftime("%H:%M:%S"),
        }

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request):
        context = base_context(request, "dashboard")
        context.update(read_model.get_dashboard(context["ui_target"].project_id))
        return templates.TemplateResponse(request=request, name="dashboard.html", context=context)

    @app.get("/tasks", response_class=HTMLResponse)
    def tasks(
        request: Request,
        status: str | None = Query(default=None),
        q: str | None = Query(default=None),
    ):
        context = base_context(request, "tasks")
        project_id = context["ui_target"].project_id
        context.update(
            {
                "tasks": read_model.list_tasks(project_id, status=status, query=q),
                "task_counts": read_model.count_tasks_by_status(project_id),
                "selected_status": status or "",
                "query": q or "",
            }
        )
        return templates.TemplateResponse(request=request, name="tasks.html", context=context)

    @app.get("/tasks/{task_id}", response_class=HTMLResponse)
    def task_detail(request: Request, task_id: str):
        context = base_context(request, "tasks")
        project_id = context["ui_target"].project_id
        task = read_model.get_task(project_id, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        context["task"] = task
        context["audit_events"] = read_model.list_audit_events(project_id, limit=200)
        return templates.TemplateResponse(request=request, name="task_detail.html", context=context)

    @app.get("/memories", response_class=HTMLResponse)
    def memories(
        request: Request,
        type: str | None = Query(default=None),  # noqa: A002 - user-facing query parameter
        q: str | None = Query(default=None),
    ):
        context = base_context(request, "memories")
        project_id = context["ui_target"].project_id
        memory_rows = read_model.list_memories(project_id, memory_type=type, query=q)
        context.update(
            {
                "memories": memory_rows,
                "grouped_memories": read_model.group_memories_by_type(memory_rows),
                "selected_type": type or "",
                "query": q or "",
            }
        )
        return templates.TemplateResponse(request=request, name="memories.html", context=context)

    @app.get("/memories/{memory_id}", response_class=HTMLResponse)
    def memory_detail(request: Request, memory_id: str):
        context = base_context(request, "memories")
        project_id = context["ui_target"].project_id
        memory = read_model.get_memory(project_id, memory_id)
        if memory is None:
            raise HTTPException(status_code=404, detail="Memory not found")
        context["memory"] = memory
        return templates.TemplateResponse(
            request=request, name="memory_detail.html", context=context
        )

    @app.get("/sessions", response_class=HTMLResponse)
    def sessions(request: Request):
        context = base_context(request, "sessions")
        context["sessions"] = read_model.list_sessions(context["ui_target"].project_id)
        return templates.TemplateResponse(request=request, name="sessions.html", context=context)

    @app.get("/sessions/{session_id}", response_class=HTMLResponse)
    def session_detail(request: Request, session_id: str):
        context = base_context(request, "sessions")
        project_id = context["ui_target"].project_id
        session = read_model.get_session(project_id, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        context["session"] = session
        return templates.TemplateResponse(
            request=request, name="session_detail.html", context=context
        )

    @app.get("/audit", response_class=HTMLResponse)
    def audit(request: Request):
        context = base_context(request, "audit")
        context["audit_events"] = read_model.list_audit_events(
            context["ui_target"].project_id, limit=200
        )
        return templates.TemplateResponse(request=request, name="audit.html", context=context)

    @app.get("/api/snapshot-version")
    def snapshot_version():
        target = active_target()
        return {
            "version": _combined_snapshot_version(target),
            "project_id": target.project_id,
            "ui_state_version": target.version,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        }

    @app.get("/api/ui-state")
    def ui_state_endpoint():
        target = active_target()
        return {
            "app": "engram-ui",
            "project_id": target.project_id,
            "project_name": target.project_name,
            "repo_path": target.repo_path,
            "version": target.version,
        }

    return app


def _combined_snapshot_version(target: ui_state.UiTarget) -> str:
    db_version = read_model.get_snapshot_version(target.project_id)
    return max(target.version, db_version)
