import json
import os

from engram.db import get_db_connection
from engram.models.project_helpers import (
    load_repo_paths,
    optional_text,
    plan_key_or_default,
    validate_active_plan,
)

_UNSET = object()


class Project:
    def __init__(
        self,
        id,
        name,
        summary=None,
        status="active",
        repo_paths=None,
        plan_key=None,
        active_plan_id=None,
    ):
        self.id = id
        self.name = name
        self.summary = summary
        self.status = status
        self.repo_paths = repo_paths or []
        self.plan_key = plan_key_or_default(plan_key, id)
        self.active_plan_id = optional_text(active_plan_id)
        self.active_plan = None

    @classmethod
    def create(
        cls,
        id,
        name,
        summary=None,
        repo_paths=None,
        db_path=None,
        plan_key=None,
        active_plan_id=None,
    ):
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        resolved_plan_key = (
            plan_key.strip() if isinstance(plan_key, str) and plan_key.strip() else id
        )
        resolved_active_plan_id = optional_text(active_plan_id)
        existing = conn.execute(
            "SELECT id FROM projects WHERE plan_key = ?",
            (resolved_plan_key,),
        ).fetchone()
        if existing and existing["id"] != id:
            conn.close()
            raise ValueError(f"Project plan key '{resolved_plan_key}' already exists.")
        if resolved_active_plan_id is not None:
            try:
                validate_active_plan(conn, id, resolved_active_plan_id)
            except Exception:
                conn.close()
                raise
        repo_paths_json = json.dumps(repo_paths or [])
        conn.execute(
            """
            INSERT INTO projects (id, plan_key, active_plan_id, name, summary, repo_paths)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (id, resolved_plan_key, resolved_active_plan_id, name, summary, repo_paths_json),
        )
        conn.commit()
        conn.close()
        return cls(
            id,
            name,
            summary,
            repo_paths=repo_paths,
            plan_key=resolved_plan_key,
            active_plan_id=resolved_active_plan_id,
        )

    @classmethod
    def _from_row(cls, row):
        """Build a Project from a SQLite row."""
        return cls(
            row["id"],
            row["name"],
            row["summary"],
            row["status"],
            load_repo_paths(row["repo_paths"]),
            plan_key_or_default(row["plan_key"] if "plan_key" in row.keys() else None, row["id"]),
            row["active_plan_id"] if "active_plan_id" in row.keys() else None,
        )

    @classmethod
    def get(cls, id, db_path=None):
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (id,)).fetchone()
        conn.close()
        if row:
            return cls._from_row(row)
        return None

    @classmethod
    def find_by_repo_path(cls, path, db_path=None):
        path = os.path.abspath(path)
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        rows = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()

        for row in rows:
            paths = load_repo_paths(row["repo_paths"])
            if path in paths:
                return cls._from_row(row)
        return None

    @classmethod
    def list_all(cls, db_path=None):
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        rows = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()
        return [cls._from_row(row) for row in rows]

    def update(self, name=None, summary=None, status=None, active_plan_id=_UNSET, db_path=None):
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        updates = []
        params = []
        if name:
            updates.append("name = ?")
            params.append(name)
            self.name = name
        if summary:
            updates.append("summary = ?")
            params.append(summary)
            self.summary = summary
        if status:
            updates.append("status = ?")
            params.append(status)
            self.status = status
        if active_plan_id is not _UNSET:
            resolved_active_plan_id = optional_text(active_plan_id)
            if resolved_active_plan_id is not None:
                try:
                    validate_active_plan(conn, self.id, resolved_active_plan_id)
                except Exception:
                    conn.close()
                    raise
            updates.append("active_plan_id = ?")
            params.append(resolved_active_plan_id)
            self.active_plan_id = resolved_active_plan_id

        if not updates:
            conn.close()
            return

        updates.append("updated_at = datetime('now')")
        params.append(self.id)

        query = f"UPDATE projects SET {', '.join(updates)} WHERE id = ?"
        conn.execute(query, params)
        conn.commit()
        conn.close()

    def get_active_plan(self, db_path=None):
        """Return the active plan for the project when one is configured."""
        if not self.active_plan_id:
            return None

        cached_plan = getattr(self, "active_plan", None)
        if cached_plan is not None and getattr(cached_plan, "id", None) == self.active_plan_id:
            return cached_plan

        from engram.models.plan import Plan

        return Plan.get(self.active_plan_id, db_path=db_path)

    def add_repo_path(self, path, db_path=None):
        path = os.path.abspath(path)
        if path not in self.repo_paths:
            self.repo_paths.append(path)
            conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
            conn.execute(
                "UPDATE projects SET repo_paths = ? WHERE id = ?",
                (json.dumps(self.repo_paths), self.id),
            )
            conn.commit()
            conn.close()
