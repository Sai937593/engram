import json
import os

from engram.db import get_db_connection


class Project:
    def __init__(self, id, name, summary=None, status="active", repo_paths=None):
        self.id = id
        self.name = name
        self.summary = summary
        self.status = status
        self.repo_paths = repo_paths or []

    @classmethod
    def create(cls, id, name, summary=None, repo_paths=None):
        conn = get_db_connection()
        repo_paths_json = json.dumps(repo_paths or [])
        conn.execute(
            "INSERT INTO projects (id, name, summary, repo_paths) VALUES (?, ?, ?, ?)",
            (id, name, summary, repo_paths_json),
        )
        conn.commit()
        conn.close()
        return cls(id, name, summary, repo_paths=repo_paths)

    @classmethod
    def get(cls, id):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (id,)).fetchone()
        conn.close()
        if row:
            paths_str = row["repo_paths"]
            paths = json.loads(paths_str) if paths_str else []
            return cls(row["id"], row["name"], row["summary"], row["status"], paths)
        return None

    @classmethod
    def find_by_repo_path(cls, path):
        path = os.path.abspath(path)
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()

        for row in rows:
            paths_str = row["repo_paths"]
            paths = json.loads(paths_str) if paths_str else []
            if path in paths:
                return cls(row["id"], row["name"], row["summary"], row["status"], paths)
        return None

    @classmethod
    def list_all(cls):
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()
        res = []
        for row in rows:
            paths_str = row["repo_paths"]
            paths = json.loads(paths_str) if paths_str else []
            res.append(cls(row["id"], row["name"], row["summary"], row["status"], paths))
        return res

    def update(self, name=None, summary=None, status=None):
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
        conn = get_db_connection()
        conn.execute(query, params)
        conn.commit()
        conn.close()

    def add_repo_path(self, path):
        path = os.path.abspath(path)
        if path not in self.repo_paths:
            self.repo_paths.append(path)
            conn = get_db_connection()
            conn.execute(
                "UPDATE projects SET repo_paths = ? WHERE id = ?",
                (json.dumps(self.repo_paths), self.id),
            )
            conn.commit()
            conn.close()
