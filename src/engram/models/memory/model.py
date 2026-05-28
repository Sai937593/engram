import uuid
from typing import Any

from engram.db import get_db_connection
from engram.models.audit import AuditLog

VALID_MEMORY_SCOPES = {"project", "task"}
VALID_PROJECT_LEVELS = {"L0", "L1", "L2", "L3"}
GUARDRAIL_DEMOTION_LEVEL_MAP = {"L0": "L1", "L1": "L2", "L2": "L3"}


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
        normalized_level = cls._validate_scope_level(scope=scope, level=level)

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
                normalized_level,
                task_id,
                ",".join(tags or []),
                1 if always_include else 0,
            ),
        )
        conn.commit()
        conn.close()

        AuditLog.log("memories", id, "create")

        return cls(
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
        )

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
        next_scope = kwargs.get("scope", self.scope)
        next_level = kwargs.get("level", self.level)
        normalized_level = self._validate_scope_level(scope=next_scope, level=next_level)
        if "level" in kwargs:
            kwargs["level"] = normalized_level

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

    def demote_project_guardrail_level(self, reason: str) -> tuple[str, str]:
        """Demote a project-scope guardrail level by exactly one level and audit the reason."""
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ValueError("Demotion reason cannot be empty.")

        if self.scope != "project":
            raise ValueError(
                f"Memory '{self.id}' is scope '{self.scope}'. Only project-scope memories can be demoted."
            )

        current_level = self._normalize_level(self.level)
        if current_level is None or current_level not in VALID_PROJECT_LEVELS:
            raise ValueError(
                f"Memory '{self.id}' has invalid level '{self.level}'. Expected one of: L0, L1, L2, L3."
            )
        if current_level == "L3":
            raise ValueError(f"Memory '{self.id}' is already at the lowest level (L3).")

        next_level = GUARDRAIL_DEMOTION_LEVEL_MAP[current_level]

        conn = get_db_connection()
        conn.execute(
            "UPDATE memories SET level = ?, updated_at = datetime('now') WHERE id = ?",
            (next_level, self.id),
        )
        conn.commit()
        conn.close()

        self.level = next_level
        AuditLog.log(
            "memories",
            self.id,
            "guardrail_demote",
            field="level",
            old_value=current_level,
            new_value=next_level,
        )
        AuditLog.log(
            "memories",
            self.id,
            "guardrail_demote",
            field="reason",
            old_value=None,
            new_value=normalized_reason,
        )

        return current_level, next_level

    @staticmethod
    def _normalize_level(level: str | None) -> str | None:
        if level is None:
            return None
        normalized_level = level.strip()
        if not normalized_level:
            return None
        return normalized_level

    @classmethod
    def _validate_scope_level(cls, scope: str, level: str | None) -> str | None:
        if scope not in VALID_MEMORY_SCOPES:
            raise ValueError(
                f"Invalid memory scope '{scope}'. Allowed values: {', '.join(sorted(VALID_MEMORY_SCOPES))}."
            )

        normalized_level = cls._normalize_level(level)
        if normalized_level is not None and normalized_level not in VALID_PROJECT_LEVELS:
            raise ValueError(
                f"Invalid memory level '{normalized_level}'. Allowed values: {', '.join(sorted(VALID_PROJECT_LEVELS))}."
            )

        if scope == "project" and normalized_level is None:
            raise ValueError("Project-scope memories require a valid level (L0, L1, L2, or L3).")
        if scope == "task" and normalized_level is not None:
            raise ValueError("Task-scope memories must not define a level.")

        return normalized_level

    def delete(self):
        conn = get_db_connection()
        conn.execute("DELETE FROM memories WHERE id = ?", (self.id,))
        conn.commit()
        conn.close()
        AuditLog.log("memories", self.id, "delete")

    @classmethod
    def list_by_project(cls, project_id: str) -> list["Memory"]:
        from engram.models.memory.queries import list_by_project

        return list_by_project(project_id)

    @classmethod
    def list_by_type(cls, project_id: str, memory_type: str) -> list["Memory"]:
        from engram.models.memory.queries import list_by_type

        return list_by_type(project_id, memory_type)

    @classmethod
    def list_project_guardrail_candidates(cls, project_id: str) -> list["Memory"]:
        from engram.models.memory.queries import list_project_guardrail_candidates

        return list_project_guardrail_candidates(project_id)

    @classmethod
    def list_task_scope_for_project(cls, project_id: str) -> list["Memory"]:
        from engram.models.memory.queries import list_task_scope_for_project

        return list_task_scope_for_project(project_id)

    @classmethod
    def list_always_include(cls, project_id: str) -> list["Memory"]:
        from engram.models.memory.queries import list_always_include

        return list_always_include(project_id)

    @classmethod
    def get(cls, id: str) -> "Memory | None":
        from engram.models.memory.queries import get

        return get(id)

    @classmethod
    def search(
        cls,
        query: str | None,
        type_filter: str | None = None,
        tag_filters: list[str] | None = None,
        project_id: str | None = None,
    ) -> list["Memory"]:
        from engram.models.memory.queries import search

        return search(query, type_filter, tag_filters, project_id)
