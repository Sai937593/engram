"""Transition SQL helpers for phase status lifecycle."""

from typing import Any


def list_other_active_phase_ids(conn: Any, project_id: str, active_phase_id: str) -> list[str]:
    """Return IDs of other active phases in the same project."""
    rows = conn.execute(
        """
        SELECT id
        FROM phases
        WHERE project_id = ? AND status = 'active' AND id != ?
        """,
        (project_id, active_phase_id),
    ).fetchall()
    return [row["id"] for row in rows]


def demote_phase_to_planned(conn: Any, phase_id: str) -> None:
    """Set one phase back to planned."""
    conn.execute(
        """
        UPDATE phases
        SET status = 'planned', updated_at = datetime('now')
        WHERE id = ?
        """,
        (phase_id,),
    )


def activate_phase(conn: Any, phase_id: str) -> None:
    """Set one phase active."""
    conn.execute(
        """
        UPDATE phases
        SET status = 'active', updated_at = datetime('now')
        WHERE id = ?
        """,
        (phase_id,),
    )
