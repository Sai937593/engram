import uuid

from engram.db import get_db_connection
from engram.models.audit import AuditLog


class Task:
    def __init__(
        self,
        id,
        project_id,
        title,
        description=None,
        status="todo",
        priority="medium",
        phase=None,
        phase_id=None,
        depends_on=None,
        acceptance=None,
        evidence=None,
        tags=None,
    ):
        self.id = id
        self.project_id = project_id
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.phase = phase
        self.phase_id = phase_id
        self.depends_on = depends_on
        self.acceptance = acceptance
        self.evidence = evidence
        self.tags = tags or []

    @classmethod
    def create(
        cls,
        project_id,
        title,
        description=None,
        status="todo",
        priority="medium",
        phase=None,
        phase_id=None,
        depends_on=None,
        acceptance=None,
        tags=None,
        id=None,
    ):
        if not id:
            id = uuid.uuid4().hex[:8]

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, description, status, priority, phase, phase_id, depends_on, acceptance, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id,
                project_id,
                title,
                description,
                status,
                priority,
                phase,
                phase_id,
                depends_on,
                acceptance,
                ",".join(tags or []),
            ),
        )
        conn.commit()
        conn.close()

        AuditLog.log("tasks", id, "create")

        return cls(
            id,
            project_id,
            title,
            description,
            status,
            priority,
            phase,
            phase_id,
            depends_on,
            acceptance,
            None,
            tags,
        )

    @classmethod
    def list_by_project(cls, project_id):
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM tasks WHERE project_id = ?", (project_id,)).fetchall()
        conn.close()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def get(cls, id):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (id,)).fetchone()
        conn.close()
        if row:
            return cls.from_row(row)
        return None

    @classmethod
    def get_next(cls, project_id: str) -> "Task | None":
        """Return the highest-priority todo task, respecting dependencies."""
        priority_order = "CASE t1.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END"
        conn = get_db_connection()
        # Find a task that is 'todo', and either has no dependency, OR its dependency is 'done'
        query = f"""
            SELECT t1.* FROM tasks t1
            LEFT JOIN tasks t2 ON t1.depends_on = t2.id
            WHERE t1.project_id = ?
              AND t1.status = 'todo'
              AND (t1.depends_on IS NULL OR t2.status = 'done')
            ORDER BY {priority_order}, t1.created_at ASC
            LIMIT 1
        """
        row = conn.execute(query, (project_id,)).fetchone()
        conn.close()
        if row:
            return cls.from_row(row)
        return None

    @classmethod
    def count_by_status(cls, project_id: str) -> dict:
        """Return a dict of status → count for all tasks in the project."""
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM tasks WHERE project_id = ? GROUP BY status",
            (project_id,),
        ).fetchall()
        conn.close()
        return {row["status"]: row["cnt"] for row in rows}

    @classmethod
    def from_row(cls, row):
        return cls(
            row["id"],
            row["project_id"],
            row["title"],
            row["description"],
            row["status"],
            row["priority"],
            row["phase"],
            row["phase_id"],
            row["depends_on"],
            row["acceptance"],
            row["evidence"],
            row["tags"].split(",") if row["tags"] else [],
        )

    def update(self, **kwargs):
        updates = []
        params = []

        # Mapping model attributes to DB columns if they differ (here they match)
        for key, value in kwargs.items():
            if hasattr(self, key):
                old_value = getattr(self, key)
                if old_value != value:
                    updates.append(f"{key} = ?")
                    params.append(value if not isinstance(value, list) else ",".join(value))
                    setattr(self, key, value)
                    AuditLog.log(
                        "tasks",
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

        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        conn = get_db_connection()
        conn.execute(query, params)
        conn.commit()
        conn.close()

    def delete(self):
        conn = get_db_connection()
        conn.execute("DELETE FROM tasks WHERE id = ?", (self.id,))
        conn.commit()
        conn.close()
        AuditLog.log("tasks", self.id, "delete")
