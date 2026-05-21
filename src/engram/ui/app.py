"""FastAPI app factory for the Engram Command Center UI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from engram.models.memory import Memory
from engram.models.task import Task
from engram.ui import read_model
from engram.ui import state as ui_state

UI_DIR = Path(__file__).parent


def create_app(state_path: Path | None = None) -> FastAPI:
    """Create the Engram UI app for the latest launched project."""
    app = FastAPI(title="Engram UI", docs_url=None, redoc_url=None)

    # API Router or just add endpoints directly
    def active_target() -> ui_state.UiTarget:
        try:
            return ui_state.require_target(state_path)
        except ui_state.UiStateError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/dashboard")
    def api_dashboard():
        target = active_target()
        project = read_model.get_project(target.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        data = read_model.get_dashboard(target.project_id)
        return {
            "project": dict(project),
            "dashboard": data,
        }

    @app.get("/api/tasks")
    def api_tasks(status: str | None = None, q: str | None = None):
        target = active_target()
        project_id = target.project_id
        tasks = read_model.list_tasks(project_id, status=status, query=q)
        return {
            "tasks": [dict(t) for t in tasks],
            "task_counts": read_model.count_tasks_by_status(project_id),
        }

    @app.get("/api/memories")
    def api_memories(type: str | None = None, q: str | None = None):
        target = active_target()
        project_id = target.project_id
        memories = read_model.list_memories(project_id, memory_type=type, query=q)
        return {
            "memories": [dict(m) for m in memories],
            "grouped": read_model.group_memories_by_type(memories),
        }

    @app.get("/api/audit")
    def api_audit():
        target = active_target()
        events = read_model.list_audit_events(target.project_id, limit=200)
        return {"audit_events": [dict(e) for e in events]}

    @app.patch("/api/tasks/{task_id}/status")
    def update_task_status(task_id: str, status: str = Body(..., embed=True)):
        target = active_target()
        task = Task.get(task_id)
        if not task or task.project_id != target.project_id:
            raise HTTPException(status_code=404, detail="Task not found")
        task.update(status=status)
        return {"success": True, "task": vars(task)}

    @app.patch("/api/memories/{memory_id}")
    def update_memory(
        memory_id: str,
        content: str | None = Body(None, embed=True),
        title: str | None = Body(None, embed=True),
    ):
        target = active_target()
        memory = Memory.get(memory_id)
        if not memory or memory.project_id != target.project_id:
            raise HTTPException(status_code=404, detail="Memory not found")
        updates = {}
        if content is not None:
            updates["content"] = content
        if title is not None:
            updates["title"] = title
        memory.update(**updates)
        return {"success": True}

    @app.get("/api/snapshot-version")
    def snapshot_version():
        target = active_target()
        db_version = read_model.get_snapshot_version(target.project_id)
        return {
            "version": max(target.version, db_version),
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

    # Mount static assets from Vite build
    dist_dir = UI_DIR / "frontend" / "dist"
    if dist_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")

    # SPA Catch-all
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        index_file = dist_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return HTMLResponse(
            "<h1>Frontend not built</h1><p>Run <code>npm run build</code> in <code>src/engram/ui/frontend</code>.</p>"
        )

    return app
