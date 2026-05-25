"""Shared helpers for task command behavior."""

import click

from engram.db import get_db_connection
from engram.models.task import Task

VALID_TASK_FIELDS = {
    "title",
    "status",
    "priority",
    "description",
    "tags",
    "acceptance",
    "phase",
    "phase_id",
    "evidence",
    "depends_on",
}
VALID_TASK_STATUSES = {"todo", "in-progress", "done", "blocked", "cancelled"}
VALID_TASK_PRIORITIES = {"low", "medium", "high", "critical"}


def resolve_task_id_in_project(value: str, project_id: str) -> str:
    """Resolve a task ID or prefix to a single task ID in the current project."""
    normalized_value = value.strip()
    if not normalized_value:
        raise click.ClickException("Task reference cannot be empty.")

    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id FROM tasks WHERE project_id = ? AND (id = ? OR id LIKE ?)",
        (project_id, normalized_value, normalized_value + "%"),
    ).fetchall()
    conn.close()

    matching_ids = sorted(list(set(row["id"] for row in rows)))

    if not matching_ids:
        raise click.ClickException(f"Task '{normalized_value}' not found in this project.")

    if len(matching_ids) > 1:
        if normalized_value in matching_ids:
            return normalized_value
        raise click.ClickException(
            f"Ambiguous task '{normalized_value}'. Multiple matches found: {', '.join(matching_ids)}"
        )

    return matching_ids[0]


def resolve_task_dependency(value: str | None, project_id: str) -> str | None:
    """Resolve a partial or exact task ID to a full 8-character ID."""
    if not value or value.lower() in ("none", "null", "clear"):
        return None
    normalized_value = value.strip()
    if not normalized_value:
        raise click.ClickException("Task dependency cannot be empty.")

    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id FROM tasks WHERE project_id = ? AND (id = ? OR id LIKE ?)",
        (project_id, normalized_value, normalized_value + "%"),
    ).fetchall()
    conn.close()

    matching_ids = sorted(list(set(row["id"] for row in rows)))

    if not matching_ids:
        raise click.ClickException(
            f"Task dependency '{normalized_value}' not found in this project."
        )

    if len(matching_ids) > 1:
        if normalized_value in matching_ids:
            return normalized_value
        raise click.ClickException(
            f"Ambiguous task dependency '{normalized_value}'. Multiple matches found: {', '.join(matching_ids)}"
        )

    return matching_ids[0]


def parse_relevant_files_csv(raw_value: str | None, option_name: str = "--files") -> list[str]:
    """Parse and validate comma-separated relevant file path input."""
    if raw_value is None:
        return []

    if not raw_value.strip():
        raise click.ClickException(f"{option_name} cannot be empty.")

    raw_entries = raw_value.split(",")
    cleaned_entries = [entry.strip() for entry in raw_entries]

    blank_positions = [str(index + 1) for index, entry in enumerate(cleaned_entries) if not entry]
    if blank_positions:
        raise click.ClickException(
            f"{option_name} contains blank path entries at position(s): {', '.join(blank_positions)}"
        )

    seen: set[str] = set()
    duplicates: list[str] = []
    for entry in cleaned_entries:
        if entry in seen and entry not in duplicates:
            duplicates.append(entry)
        seen.add(entry)

    if duplicates:
        raise click.ClickException(
            f"{option_name} contains duplicate path(s): {', '.join(duplicates)}"
        )

    return cleaned_entries


def check_dependency_cycle(task_id: str, depends_on_id: str | None, project_id: str) -> None:
    """Validate that the dependency edge does not create a cycle."""
    if not depends_on_id:
        return

    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, depends_on FROM tasks WHERE project_id = ?", (project_id,)
    ).fetchall()
    conn.close()

    dep_map = {row["id"]: row["depends_on"] for row in rows}
    dep_map[task_id] = depends_on_id

    visited = set()
    path = set()

    def dfs(node: str) -> bool:
        if node in path:
            return True
        if node in visited:
            return False

        path.add(node)
        dep = dep_map.get(node)
        if dep:
            if dfs(dep):
                return True
        path.remove(node)
        visited.add(node)
        return False

    if dfs(task_id):
        raise click.ClickException("Circular dependency detected.")


def get_effective_status(task: Task) -> str:
    """Calculate the implicit/effective status of a task based on dependencies."""
    if task.status in ("done", "cancelled"):
        return task.status

    visited = set()
    curr = task
    has_unfinished = False
    has_blocked = False
    has_cancelled = False

    while curr.depends_on:
        if curr.depends_on in visited:
            break
        visited.add(curr.depends_on)
        dep = Task.get(curr.depends_on)
        if not dep:
            break
        if dep.status == "cancelled":
            has_cancelled = True
            break
        if dep.status == "blocked":
            has_blocked = True
        elif dep.status != "done":
            has_unfinished = True
        curr = dep

    if has_cancelled:
        return "cancelled"
    if has_blocked or has_unfinished:
        return "blocked"

    return task.status


def blocked_dependency_messages(task: Task, include_status: bool) -> list[str]:
    """Return blocker messages for a task's unfinished dependency chain."""
    visited = set()
    curr = task
    blockers: list[str] = []

    while curr.depends_on:
        if curr.depends_on in visited:
            break
        visited.add(curr.depends_on)
        dep = Task.get(curr.depends_on)
        if not dep:
            break
        if dep.status != "done":
            if include_status:
                blockers.append(f"'{dep.id}' ({dep.title}, status: {dep.status})")
            else:
                blockers.append(f"'{dep.id}' ({dep.title})")
        curr = dep

    return blockers
