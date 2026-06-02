import json
import os

from engram.db import get_db_connection


class Project:
    def __init__(self, id, name, summary=None, status="active", repo_paths=None, plan_key=None):
        self.id = id
        self.name = name
        self.summary = summary
        self.status = status
        self.repo_paths = repo_paths or []
        self.plan_key = plan_key or id

    @classmethod
    def create(cls, id, name, summary=None, repo_paths=None, db_path=None, plan_key=None):
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        resolved_plan_key = (
            plan_key.strip() if isinstance(plan_key, str) and plan_key.strip() else id
        )
        existing = conn.execute(
            "SELECT id FROM projects WHERE plan_key = ?",
            (resolved_plan_key,),
        ).fetchone()
        if existing and existing["id"] != id:
            conn.close()
            raise ValueError(f"Project plan key '{resolved_plan_key}' already exists.")
        repo_paths_json = json.dumps(repo_paths or [])
        conn.execute(
            "INSERT INTO projects (id, plan_key, name, summary, repo_paths) VALUES (?, ?, ?, ?, ?)",
            (id, resolved_plan_key, name, summary, repo_paths_json),
        )
        conn.commit()
        conn.close()
        return cls(id, name, summary, repo_paths=repo_paths, plan_key=resolved_plan_key)

    @classmethod
    def get(cls, id, db_path=None):
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (id,)).fetchone()
        conn.close()
        if row:
            return cls(
                row["id"],
                row["name"],
                row["summary"],
                row["status"],
                json.loads(row["repo_paths"]),
                row["plan_key"] if "plan_key" in row.keys() else row["id"],
            )
        return None

    @classmethod
    def find_by_repo_path(cls, path, db_path=None):
        path = os.path.abspath(path)
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        rows = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()

        for row in rows:
            paths = json.loads(row["repo_paths"])
            if path in paths:
                return cls(
                    row["id"],
                    row["name"],
                    row["summary"],
                    row["status"],
                    paths,
                    row["plan_key"] if "plan_key" in row.keys() else row["id"],
                )
        return None

    @classmethod
    def list_all(cls, db_path=None):
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        rows = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()
        return [
            cls(
                row["id"],
                row["name"],
                row["summary"],
                row["status"],
                json.loads(row["repo_paths"]),
                row["plan_key"] if "plan_key" in row.keys() else row["id"],
            )
            for row in rows
        ]

    def update(self, name=None, summary=None, status=None, db_path=None):
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

        if not updates:
            return

        updates.append("updated_at = datetime('now')")
        params.append(self.id)

        query = f"UPDATE projects SET {', '.join(updates)} WHERE id = ?"
        conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
        conn.execute(query, params)
        conn.commit()
        conn.close()

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
