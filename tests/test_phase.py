"""Tests for the Phase domain model CRUD helpers."""

import pytest

from engram.models.phase import Phase


def test_create_phase_defaults(project):
    phase = Phase.create(project_id=project.id, title="Phase 1")
    assert phase.title == "Phase 1"
    assert phase.status == "planned"
    assert phase.order_index == 0


def test_create_phase_defaults_order_index_to_next_value(project):
    first = Phase.create(project_id=project.id, title="Phase 1")
    second = Phase.create(project_id=project.id, title="Phase 2")
    assert first.order_index == 0
    assert second.order_index == 1


def test_create_phase_with_explicit_status_and_order(project):
    phase = Phase.create(
        project_id=project.id,
        title="Blocked Stage",
        status="blocked",
        order_index=5,
    )
    assert phase.status == "blocked"
    assert phase.order_index == 5


def test_create_phase_rejects_invalid_status(project):
    with pytest.raises(ValueError, match="Invalid phase status"):
        Phase.create(project_id=project.id, title="Bad", status="todo")


def test_get_phase(project):
    created = Phase.create(project_id=project.id, title="Implement Model")
    fetched = Phase.get(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == "Implement Model"


def test_get_nonexistent_phase(tmp_db):
    assert Phase.get("does-not-exist") is None


def test_list_phases_by_project_ordered_by_order_index(project):
    Phase.create(project_id=project.id, title="Third", order_index=2)
    Phase.create(project_id=project.id, title="First", order_index=0)
    Phase.create(project_id=project.id, title="Second", order_index=1)
    phases = Phase.list_by_project(project.id)
    assert [phase.title for phase in phases] == ["First", "Second", "Third"]


def test_update_phase_fields(project):
    phase = Phase.create(project_id=project.id, title="Old Title", status="planned")
    phase.update(
        title="New Title",
        description="Updated description",
        status="active",
        acceptance="All done",
        evidence="Shipped",
        order_index=9,
    )
    refreshed = Phase.get(phase.id)
    assert refreshed is not None
    assert refreshed.title == "New Title"
    assert refreshed.description == "Updated description"
    assert refreshed.status == "active"
    assert refreshed.acceptance == "All done"
    assert refreshed.evidence == "Shipped"
    assert refreshed.order_index == 9


def test_update_phase_rejects_invalid_status(project):
    phase = Phase.create(project_id=project.id, title="Phase")
    with pytest.raises(ValueError, match="Invalid phase status"):
        phase.update(status="todo")
