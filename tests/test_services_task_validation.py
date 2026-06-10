import pytest

from engram.services.errors import ValidationError
from engram.services.task.validation import validate_priority_field, validate_status_field


def test_validate_priority_field_valid():
    """Test that valid priorities do not raise errors."""
    for priority in ["critical", "high", "medium", "low"]:
        validate_priority_field(priority)


def test_validate_priority_field_invalid():
    """Test that invalid priorities raise ValidationError."""
    with pytest.raises(ValidationError) as exc:
        validate_priority_field("invalid")

    assert exc.value.code == "INVALID_TASK_PRIORITY"
    assert exc.value.message == "Task priority is invalid."
    assert exc.value.details == {
        "priority": "invalid",
        "allowed_priorities": ["critical", "high", "low", "medium"],
    }


def test_validate_status_field_valid():
    """Test that valid statuses do not raise errors."""
    for status in ["todo", "in-progress", "done", "blocked", "cancelled"]:
        validate_status_field(status)


def test_validate_status_field_invalid():
    """Test that invalid statuses raise ValidationError."""
    with pytest.raises(ValidationError) as exc:
        validate_status_field("invalid")

    assert exc.value.code == "INVALID_TASK_STATUS"
    assert exc.value.message == "Task status is invalid."
    assert exc.value.details == {
        "status": "invalid",
        "allowed_statuses": ["blocked", "cancelled", "done", "in-progress", "todo"],
    }


def test_validate_status_field_all_is_invalid():
    """Test that 'all' is an invalid status field."""
    with pytest.raises(ValidationError) as exc:
        validate_status_field("all")

    assert exc.value.code == "INVALID_TASK_STATUS"
    assert exc.value.message == "Task status is invalid."
    assert exc.value.details == {
        "status": "all",
        "allowed_statuses": ["blocked", "cancelled", "done", "in-progress", "todo"],
    }
