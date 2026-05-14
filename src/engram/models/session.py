import uuid
from datetime import datetime

from engram.db import get_db_connection
from engram.models.audit import AuditLog


class Session:
    def __init__(
        self,
        id,
        project_id,
        goal=None,
        status="open",
        summary=None,
        changed_files=None,
        checks_run=None,
        next_steps=None,
        next_task_id=None,
        started_at=None,
        closed_at=None,
    ):
        self.id = id
        self.project_id = project_id
        self.goal = goal
        self.status = status
        self.summary = summary
        self.changed_files = changed_files
        self.checks_run = checks_run
        self.next_steps = next_steps
        self.next_task_id = next_task_id
        self.started_at = started_at
        self.closed_at = closed_at

    @classmethod
    def create(cls, project_id, goal=None):
        # Close any existing open sessions for this project first?
        # For simplicity, we'll allow it but usually there should only be one.

        id = uuid.uuid4().hex[:8]
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO sessions (id, project_id, goal) VALUES (?, ?, ?)", (id, project_id, goal)
        )
        conn.commit()
        conn.close()

        AuditLog.log("sessions", id, "create")
        return cls.get(id)

    @classmethod
    def get(cls, id):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (id,)).fetchone()
        conn.close()
        if row:
            return cls.from_row(row)
        return None

    @classmethod
    def get_active(cls, project_id):
        conn = get_db_connection()
        row = conn.execute(
            "SELECT * FROM sessions WHERE project_id = ? AND status = 'open' ORDER BY started_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        conn.close()
        if row:
            return cls.from_row(row)
        return None

    @classmethod
    def list_by_project(cls, project_id):
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT * FROM sessions WHERE project_id = ? ORDER BY started_at DESC", (project_id,)
        ).fetchall()
        conn.close()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def get_latest_closed(cls, project_id):
        """Return the most recently closed session for a project."""
        conn = get_db_connection()
        row = conn.execute(
            "SELECT * FROM sessions WHERE project_id = ? AND status = 'closed' ORDER BY closed_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        conn.close()
        if row:
            return cls.from_row(row)
        return None

    @classmethod
    def from_row(cls, row):
        return cls(
            row["id"],
            row["project_id"],
            row["goal"],
            row["status"],
            row["summary"],
            row["changed_files"],
            row["checks_run"],
            row["next_steps"],
            row["next_task_id"],
            row["started_at"],
            row["closed_at"],
        )

    def close(
        self, summary=None, changed_files=None, checks_run=None, next_steps=None, next_task_id=None
    ):
        self.status = "closed"
        self.summary = summary
        self.changed_files = changed_files
        self.checks_run = checks_run
        self.next_steps = next_steps
        self.next_task_id = next_task_id
        self.closed_at = datetime.now().isoformat()

        conn = get_db_connection()
        conn.execute(
            """
            UPDATE sessions
            SET status = 'closed', summary = ?, changed_files = ?, checks_run = ?,
                next_steps = ?, next_task_id = ?, closed_at = ?
            WHERE id = ?
            """,

            (
                self.summary,
                self.changed_files,
                self.checks_run,
                self.next_steps,
                self.next_task_id,
                self.closed_at,
                self.id,
            ),
        )
        conn.commit()
        conn.close()

        AuditLog.log("sessions", self.id, "close")

    def update(self, **kwargs):
        updates = []
        params = []
        for key, value in kwargs.items():
            if hasattr(self, key):
                updates.append(f"{key} = ?")
                params.append(value)
                setattr(self, key, value)
                AuditLog.log("sessions", self.id, "update", field=key)

        if not updates:
            return

        updates.append("updated_at = datetime('now')")
        params.append(self.id)
        query = f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?"
        conn = get_db_connection()
        conn.execute(query, params)
        conn.commit()
        conn.close()
