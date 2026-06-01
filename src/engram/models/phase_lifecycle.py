"""Phase status transition helpers."""

from __future__ import annotations

from engram.db import get_db_connection
from engram.models.audit import AuditLog
from engram.models.phase_transitions import (
    activate_phase,
    demote_phase_to_planned,
    list_other_active_phase_ids,
)


def start_phase(phase_id: str, project_id: str, current_status: str) -> int:
    """Set a phase active and demote other active phases in the same project."""
    conn = get_db_connection()
    audit_events: list[dict[str, str]] = []
    demoted_ids = list_other_active_phase_ids(conn, project_id, phase_id)
    for demoted_id in demoted_ids:
        demote_phase_to_planned(conn, demoted_id)
        audit_events.append(
            {"target_id": demoted_id, "old_value": "active", "new_value": "planned"}
        )
    if current_status != "active":
        activate_phase(conn, phase_id)
        audit_events.append(
            {"target_id": phase_id, "old_value": str(current_status), "new_value": "active"}
        )
    conn.commit()
    conn.close()
    for event in audit_events:
        AuditLog.log(
            "phases",
            event["target_id"],
            "update",
            field="status",
            old_value=event["old_value"],
            new_value=event["new_value"],
        )
    return len(demoted_ids)
