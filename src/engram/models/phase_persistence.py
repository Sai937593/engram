"""Low-level SQL helpers for phase model persistence."""

from typing import Any


def resolve_next_order_index(conn: Any, project_id: str) -> int:
    """Return the next order index for a project's phases."""
    row = conn.execute(
        """
        SELECT COALESCE(MAX(order_index), -1) + 1 AS next_order_index
        FROM phases
        WHERE project_id = ?
        """,
        (project_id,),
    ).fetchone()
    return int(row["next_order_index"])


def insert_phase(
    conn: Any,
    phase_id: str,
    project_id: str,
    title: str,
    description: str | None,
    status: str,
    order_index: int,
    acceptance: str | None,
    evidence: str | None,
) -> None:
    """Insert a phase row."""
    conn.execute(
        """
        INSERT INTO phases (id, project_id, title, description, status, order_index, acceptance, evidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            phase_id,
            project_id,
            title,
            description,
            status,
            order_index,
            acceptance,
            evidence,
        ),
    )


def fetch_phase_row(conn: Any, phase_id: str) -> Any:
    """Fetch one phase row by ID."""
    return conn.execute("SELECT * FROM phases WHERE id = ?", (phase_id,)).fetchone()


def fetch_project_phase_rows(conn: Any, project_id: str) -> list[Any]:
    """Fetch all project phases ordered for display/workflow."""
    return conn.execute(
        """
        SELECT * FROM phases
        WHERE project_id = ?
        ORDER BY order_index ASC, created_at ASC
        """,
        (project_id,),
    ).fetchall()


def update_phase_fields(conn: Any, phase_id: str, updates: dict[str, Any]) -> None:
    """Apply partial field updates and refresh updated_at."""
    if not updates:
        return

    set_fragments = [f"{key} = ?" for key in updates]
    params = list(updates.values())
    set_fragments.append("updated_at = datetime('now')")
    params.append(phase_id)
    conn.execute(f"UPDATE phases SET {', '.join(set_fragments)} WHERE id = ?", params)
