"""Tests for validate_and_resolve_update in task crud service."""

from __future__ import annotations

import pytest

from engram.models.phase import Phase
from engram.models.task import Task
from engram.services.errors import ValidationError
from engram.services.task.crud import validate_and_resolve_update


def test_validate_and_resolve_update_unknown_fields(tmp_db, project, task):
    """It should raise ValidationError when unknown fields are provided."""
    with pytest.raises(ValidationError) as exc:
        validate_and_resolve_update(
            project.id, task.id, task, unknown_field="value", another_unknown=123
        )

    assert exc.value.code == "UNKNOWN_UPDATE_FIELDS"
    assert "unknown_field" in exc.value.details["unknown_fields"]
    assert "another_unknown" in exc.value.details["unknown_fields"]


def test_validate_and_resolve_update_valid_status_and_priority(tmp_db, project, task):
    """It should validate valid status and priority fields."""
    resolved = validate_and_resolve_update(
        project.id, task.id, task, status="in-progress", priority="low"
    )
    assert resolved["status"] == "in-progress"
    assert resolved["priority"] == "low"

    # Testing invalid values
    with pytest.raises(ValidationError) as exc:
        validate_and_resolve_update(project.id, task.id, task, status="invalid-status")
    assert exc.value.code == "INVALID_TASK_STATUS"

    with pytest.raises(ValidationError) as exc:
        validate_and_resolve_update(project.id, task.id, task, priority="invalid-priority")
    assert exc.value.code == "INVALID_TASK_PRIORITY"


def test_validate_and_resolve_update_depends_on_clear(tmp_db, project, task):
    """It should clear depends_on when passed specific clear values."""
    clear_values = [None, "none", "null", "clear", " ", ""]
    for val in clear_values:
        resolved = validate_and_resolve_update(project.id, task.id, task, depends_on=val)
        assert resolved["depends_on"] is None


def test_validate_and_resolve_update_depends_on_invalid_type(tmp_db, project, task):
    """It should raise ValidationError if depends_on is not a string."""
    with pytest.raises(ValidationError) as exc:
        validate_and_resolve_update(project.id, task.id, task, depends_on=123)
    assert exc.value.code == "INVALID_DEPENDENCY"


def test_validate_and_resolve_update_depends_on_not_found(tmp_db, project, task):
    """It should raise ValidationError if dependency task is not found."""
    with pytest.raises(ValidationError) as exc:
        validate_and_resolve_update(project.id, task.id, task, depends_on="nonexistent-task")
    assert exc.value.code == "TASK_NOT_FOUND"


def test_validate_and_resolve_update_depends_on_self(tmp_db, project, task):
    """It should raise ValidationError if task depends on itself."""
    with pytest.raises(ValidationError) as exc:
        validate_and_resolve_update(project.id, task.id, task, depends_on=task.id)
    assert exc.value.code == "DEPENDENCY_CYCLE"


def test_validate_and_resolve_update_depends_on_cycle(tmp_db, project, task):
    """It should raise ValidationError if task dependency creates a cycle."""
    t2 = Task.create(project_id=project.id, title="Task 2", depends_on=task.id)
    with pytest.raises(ValidationError) as exc:
        validate_and_resolve_update(project.id, task.id, task, depends_on=t2.id)
    assert exc.value.code == "DEPENDENCY_CYCLE"


def test_validate_and_resolve_update_depends_on_valid(tmp_db, project, task):
    """It should resolve depends_on to the task ID."""
    t2 = Task.create(project_id=project.id, title="Task 2")
    resolved = validate_and_resolve_update(project.id, task.id, task, depends_on=t2.id)
    assert resolved["depends_on"] == t2.id


def test_validate_and_resolve_update_phase_id_clear(tmp_db, project, task):
    """It should clear phase_id and phase when passed specific clear values."""
    clear_values = [None, "none", "null", "clear", " ", ""]
    for val in clear_values:
        resolved = validate_and_resolve_update(project.id, task.id, task, phase_id=val)
        assert resolved["phase_id"] is None
        assert resolved["phase"] is None


def test_validate_and_resolve_update_phase_id_invalid(tmp_db, project, task):
    """It should raise ValidationError if phase_id is invalid type or empty."""
    with pytest.raises(ValidationError) as exc:
        validate_and_resolve_update(project.id, task.id, task, phase_id=123)
    assert exc.value.code == "INVALID_PHASE_REFERENCE"


def test_validate_and_resolve_update_phase_id_exact_match(tmp_db, project, task):
    """It should resolve phase_id when exact ID is provided."""
    phase = Phase.create(project_id=project.id, title="Test Phase")
    resolved = validate_and_resolve_update(project.id, task.id, task, phase_id=phase.id)
    assert resolved["phase_id"] == phase.id
    assert resolved["phase"] == phase.title


def test_validate_and_resolve_update_phase_id_title_match(tmp_db, project, task):
    """It should resolve phase_id when a unique title is provided."""
    phase = Phase.create(project_id=project.id, title="Unique Phase Title")
    resolved = validate_and_resolve_update(project.id, task.id, task, phase_id="unique phase title")
    assert resolved["phase_id"] == phase.id
    assert resolved["phase"] == phase.title


def test_validate_and_resolve_update_phase_id_not_found(tmp_db, project, task):
    """It should raise ValidationError if phase is not found."""
    with pytest.raises(ValidationError) as exc:
        validate_and_resolve_update(project.id, task.id, task, phase_id="nonexistent-phase")
    assert exc.value.code == "PHASE_NOT_FOUND"


def test_validate_and_resolve_update_phase_id_ambiguous(tmp_db, project, task):
    """It should raise ValidationError if phase title is ambiguous."""
    Phase.create(project_id=project.id, title="Ambiguous Phase")
    Phase.create(project_id=project.id, title="Ambiguous Phase")
    with pytest.raises(ValidationError) as exc:
        validate_and_resolve_update(project.id, task.id, task, phase_id="ambiguous phase")
    assert exc.value.code == "AMBIGUOUS_PHASE"


def test_validate_and_resolve_update_first_class_link_enforced(tmp_db, project, task):
    """It should enforce first-class phase link check when legacy phase text is updated."""
    task.update(phase_id="some-phase-id")

    with pytest.raises(ValidationError) as exc:
        validate_and_resolve_update(project.id, task.id, task, phase="New Phase Title")

    assert exc.value.code == "PHASE_LINKED_TO_FIRST_CLASS"


def test_validate_and_resolve_update_first_class_link_override_with_phase_id(tmp_db, project, task):
    """It should allow legacy phase update if phase_id is also updated/cleared."""
    task.update(phase_id="some-phase-id")

    # If phase_id is passed as None, the link is broken so we can update phase
    resolved = validate_and_resolve_update(
        project.id, task.id, task, phase_id=None, phase="New Phase Title"
    )
    assert resolved["phase_id"] is None
    assert (
        resolved["phase"] is None
    )  # Wait, wait... `validate_and_resolve_update` clears phase if `phase_id` is cleared!
