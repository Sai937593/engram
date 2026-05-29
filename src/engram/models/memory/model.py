import uuid
from typing import Any

from engram.db import get_db_connection
from engram.models.audit import AuditLog
from engram.models.memory.helpers import (
    _validate_scope_level,
    update_memory_record,
)
from engram.models.memory.helpers import (
    demote_project_guardrail_level as _demote_project_guardrail_level,
)


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
        superseded_by: str | None = None,
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
        self.superseded_by = superseded_by

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
        supersedes: str | None = None,
    ) -> "Memory":
        if not id:
            id = uuid.uuid4().hex[:8]
        normalized_level = _validate_scope_level(scope=scope, level=level)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO memories (
                id, project_id, type, title, content, scope, level, task_id, tags, always_include, superseded_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id,
                project_id,
                type,
                title,
                content,
                scope,
                normalized_level,
                task_id,
                ",".join(tags or []),
                1 if always_include else 0,
                None,
            ),
        )
        conn.commit()
        conn.close()

        AuditLog.log("memories", id, "create")

        new_memory = cls(
            id,
            project_id,
            type,
            title,
            content,
            scope,
            task_id,
            tags,
            always_include,
            normalized_level,
            None,
        )

        if supersedes:
            old_memory = cls.get(supersedes)
            if not old_memory:
                raise ValueError(f"Memory with ID {supersedes} to supersede not found.")
            old_memory.update(superseded_by=id)

        return new_memory

    @classmethod
    def from_row(cls, row: Any) -> "Memory":
        level = row["level"] if "level" in row.keys() else None
        superseded_by = row["superseded_by"] if "superseded_by" in row.keys() else None
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
            superseded_by,
        )

    def update(self, **kwargs):
        update_memory_record(self, **kwargs)

    def demote_project_guardrail_level(self, reason: str) -> tuple[str, str]:
        """Demote a project-scope guardrail level by exactly one level and audit the reason."""
        return _demote_project_guardrail_level(self, reason)

    def delete(self):
        conn = get_db_connection()
        conn.execute("DELETE FROM memories WHERE id = ?", (self.id,))
        conn.commit()
        conn.close()
        AuditLog.log("memories", self.id, "delete")


# Dynamically bind classmethods to prevent model.py from exceeding line limits and prevent circular imports
Memory.list_by_project = classmethod(
    lambda cls, *args, **kwargs: __import__(
        "engram.models.memory.queries", fromlist=["list_by_project"]
    ).list_by_project(*args, **kwargs)
)
Memory.list_by_type = classmethod(
    lambda cls, *args, **kwargs: __import__(
        "engram.models.memory.queries", fromlist=["list_by_type"]
    ).list_by_type(*args, **kwargs)
)
Memory.list_project_guardrail_candidates = classmethod(
    lambda cls, *args, **kwargs: __import__(
        "engram.models.memory.queries", fromlist=["list_project_guardrail_candidates"]
    ).list_project_guardrail_candidates(*args, **kwargs)
)
Memory.list_task_scope_for_project = classmethod(
    lambda cls, *args, **kwargs: __import__(
        "engram.models.memory.queries", fromlist=["list_task_scope_for_project"]
    ).list_task_scope_for_project(*args, **kwargs)
)
Memory.list_always_include = classmethod(
    lambda cls, *args, **kwargs: __import__(
        "engram.models.memory.queries", fromlist=["list_always_include"]
    ).list_always_include(*args, **kwargs)
)
Memory.get = classmethod(
    lambda cls, *args, **kwargs: __import__("engram.models.memory.queries", fromlist=["get"]).get(
        *args, **kwargs
    )
)
Memory.search = classmethod(
    lambda cls, *args, **kwargs: __import__(
        "engram.models.memory.queries", fromlist=["search"]
    ).search(*args, **kwargs)
)
