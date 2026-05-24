import uuid
from typing import Any

from engram.db import get_db_connection
from engram.models.audit import AuditLog


class Memory:
    def __init__(
        self,
        id: str,
        project_id: str,
        type: str,
        title: str,
        content: str,
        scope: str = "project",
        task_id: str | None = None,
        tags: list[str] | None = None,
        always_include: bool = False,
        level: str | None = None,
    ) -> None:
        self.id = id
        self.project_id = project_id
        self.type = type
        self.title = title
        self.content = content
        self.scope = scope
        self.level = level
        self.task_id = task_id
        self.tags = tags or []
        self.always_include = always_include

    @classmethod
    def create(
        cls,
        project_id: str,
        type: str,
        title: str,
        content: str,
        scope: str = "project",
        task_id: str | None = None,
        tags: list[str] | None = None,
        always_include: bool = False,
        level: str | None = None,
        id: str | None = None,
    ) -> "Memory":
        if not id:
            id = uuid.uuid4().hex[:8]

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO memories (
                id, project_id, type, title, content, scope, level, task_id, tags, always_include
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id,
                project_id,
                type,
                title,
                content,
                scope,
                level,
                task_id,
                ",".join(tags or []),
                1 if always_include else 0,
            ),
        )
        conn.commit()
        conn.close()

        AuditLog.log("memories", id, "create")

        return cls(
            id, project_id, type, title, content, scope, task_id, tags, always_include, level
        )

    @classmethod
    def list_by_project(cls, project_id: str) -> list["Memory"]:
        """Return all memories for a project ordered by creation date."""
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT * FROM memories WHERE project_id = ? ORDER BY created_at ASC", (project_id,)
        ).fetchall()
        conn.close()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def list_by_type(cls, project_id: str, memory_type: str) -> list["Memory"]:
        """Return memories of a specific type for a project, ordered by creation date."""
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT * FROM memories WHERE project_id = ? AND type = ? ORDER BY created_at ASC",
            (project_id, memory_type),
        ).fetchall()
        conn.close()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def list_always_include(cls, project_id):
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT * FROM memories WHERE project_id = ? AND always_include = 1", (project_id,)
        ).fetchall()
        conn.close()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def get(cls, id):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (id,)).fetchone()
        conn.close()
        if row:
            return cls.from_row(row)
        return None

    @classmethod
    def from_row(cls, row: Any) -> "Memory":
        level = row["level"] if "level" in row.keys() else None
        return cls(
            row["id"],
            row["project_id"],
            row["type"],
            row["title"],
            row["content"],
            row["scope"],
            row["task_id"],
            row["tags"].split(",") if row["tags"] else [],
            bool(row["always_include"]),
            level,
        )

    def update(self, **kwargs):
        updates = []
        params = []

        for key, value in kwargs.items():
            if hasattr(self, key):
                old_value = getattr(self, key)
                if old_value != value:
                    updates.append(f"{key} = ?")
                    if key == "tags":
                        params.append(",".join(value))
                    elif key == "always_include":
                        params.append(1 if value else 0)
                    else:
                        params.append(value)

                    setattr(self, key, value)
                    AuditLog.log(
                        "memories",
                        self.id,
                        "update",
                        field=key,
                        old_value=str(old_value),
                        new_value=str(value),
                    )

        if not updates:
            return

        updates.append("updated_at = datetime('now')")
        params.append(self.id)

        query = f"UPDATE memories SET {', '.join(updates)} WHERE id = ?"
        conn = get_db_connection()
        conn.execute(query, params)
        conn.commit()
        conn.close()

    def delete(self):
        conn = get_db_connection()
        conn.execute("DELETE FROM memories WHERE id = ?", (self.id,))
        conn.commit()
        conn.close()
        AuditLog.log("memories", self.id, "delete")

    @classmethod
    def search(cls, query, type_filter=None, tag_filters=None):
        conn = get_db_connection()

        sql = """
            SELECT m.* FROM memories m
            JOIN memories_fts f ON m.rowid = f.rowid
            WHERE memories_fts MATCH ?
        """
        params = [query]

        if type_filter:
            sql += " AND m.type = ?"
            params.append(type_filter)

        if tag_filters:
            for tag in tag_filters:
                # Simple LIKE search for tags in MVP
                sql += " AND m.tags LIKE ?"
                params.append(f"%{tag}%")

        sql += " ORDER BY rank"

        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [cls.from_row(row) for row in rows]
