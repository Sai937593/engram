"""Tests for low-level phase transition SQL helpers."""

from engram.db import get_db_connection
from engram.models.phase import Phase
from engram.models.phase_transitions import (
    activate_phase,
    demote_phase_to_planned,
    list_other_active_phase_ids,
)


def test_phase_transition_helpers_scope_active_phase_ids_and_update_statuses(project) -> None:
    active = Phase.create(project_id=project.id, id="pha00001", title="Active", status="active")
    other_active = Phase.create(
        project_id=project.id,
        id="pha00002",
        title="Other Active",
        status="active",
    )
    planned = Phase.create(project_id=project.id, id="pha00003", title="Planned", status="planned")

    conn = get_db_connection()
    try:
        assert list_other_active_phase_ids(conn, project.id, active.id) == [other_active.id]

        demote_phase_to_planned(conn, other_active.id)
        activate_phase(conn, planned.id)
        conn.commit()
    finally:
        conn.close()

    assert Phase.get(other_active.id).status == "planned"
    assert Phase.get(planned.id).status == "active"
