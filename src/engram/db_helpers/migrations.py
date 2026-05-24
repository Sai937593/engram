"""Database migration helpers."""

import sqlite3
import uuid


def column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    """Return whether a column exists on a table."""
    rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def normalize_phase_title(phase: str | None) -> str:
    """Normalize phase titles for matching and deduplication."""
    if phase is None:
        return ""
    return " ".join(phase.split()).casefold()


def apply_tasks_column_migrations(cursor: sqlite3.Cursor) -> None:
    """Add missing legacy tasks columns for compatibility."""
    if not column_exists(cursor, "tasks", "depends_on"):
        cursor.execute("ALTER TABLE tasks ADD COLUMN depends_on TEXT REFERENCES tasks(id)")
    if not column_exists(cursor, "tasks", "phase_id"):
        cursor.execute("ALTER TABLE tasks ADD COLUMN phase_id TEXT REFERENCES phases(id)")


def apply_memories_column_migrations(cursor: sqlite3.Cursor) -> None:
    """Add missing legacy memories columns for compatibility."""
    if not column_exists(cursor, "memories", "level"):
        cursor.execute("ALTER TABLE memories ADD COLUMN level TEXT")


def backfill_legacy_phase_ids(cursor: sqlite3.Cursor) -> None:
    """Create first-class phases from legacy task.phase text and backfill phase_id."""
    legacy_rows = cursor.execute(
        """
        SELECT id, project_id, phase
        FROM tasks
        WHERE phase_id IS NULL AND phase IS NOT NULL
        """
    ).fetchall()
    if not legacy_rows:
        return

    grouped_task_ids: dict[tuple[str, str], list[str]] = {}
    display_title_by_key: dict[tuple[str, str], str] = {}
    for row in legacy_rows:
        cleaned_title = " ".join(row["phase"].split())
        normalized_title = normalize_phase_title(cleaned_title)
        if not normalized_title:
            continue

        key = (row["project_id"], normalized_title)
        grouped_task_ids.setdefault(key, []).append(row["id"])
        display_title_by_key.setdefault(key, cleaned_title)

    if not grouped_task_ids:
        return

    project_ids = sorted({project_id for project_id, _ in grouped_task_ids.keys()})
    placeholders = ",".join("?" for _ in project_ids)

    phase_id_by_key: dict[tuple[str, str], str] = {}
    existing_phase_rows = cursor.execute(
        f"""
        SELECT id, project_id, title
        FROM phases
        WHERE project_id IN ({placeholders})
        """,
        project_ids,
    ).fetchall()
    for row in existing_phase_rows:
        normalized_title = normalize_phase_title(row["title"])
        if not normalized_title:
            continue
        phase_id_by_key.setdefault((row["project_id"], normalized_title), row["id"])

    next_order_index_by_project = {project_id: -1 for project_id in project_ids}
    max_order_rows = cursor.execute(
        f"""
        SELECT project_id, COALESCE(MAX(order_index), -1) AS max_order_index
        FROM phases
        WHERE project_id IN ({placeholders})
        GROUP BY project_id
        """,
        project_ids,
    ).fetchall()
    for row in max_order_rows:
        next_order_index_by_project[row["project_id"]] = int(row["max_order_index"])

    for key, task_ids in grouped_task_ids.items():
        project_id, _ = key
        phase_id = phase_id_by_key.get(key)
        if phase_id is None:
            next_order_index_by_project[project_id] += 1
            phase_id = uuid.uuid4().hex[:8]
            cursor.execute(
                """
                INSERT INTO phases (id, project_id, title, status, order_index)
                VALUES (?, ?, ?, 'planned', ?)
                """,
                (
                    phase_id,
                    project_id,
                    display_title_by_key[key],
                    next_order_index_by_project[project_id],
                ),
            )
            phase_id_by_key[key] = phase_id

        task_placeholders = ",".join("?" for _ in task_ids)
        cursor.execute(
            f"""
            UPDATE tasks
            SET phase_id = ?
            WHERE id IN ({task_placeholders}) AND phase_id IS NULL
            """,
            [phase_id, *task_ids],
        )


def apply_task_status_migrations(cursor: sqlite3.Cursor) -> None:
    """Normalize legacy task statuses."""
    cursor.execute("UPDATE tasks SET status = 'todo' WHERE status = 'backlog'")
    cursor.execute("UPDATE tasks SET status = 'done' WHERE status = 'completed'")
