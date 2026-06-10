import pytest

from engram.services.errors import ValidationError
from engram.services.task.validation import VALID_TASK_STATUSES, validate_status_field


def test_validate_status_field_valid():
    """Test that valid statuses pass validation."""
    valid_statuses = VALID_TASK_STATUSES - {"all"}
    for status in valid_statuses:
        # Should not raise an exception
        validate_status_field(status)


def test_validate_status_field_invalid_all():
    """Test that 'all' is an invalid status."""
    with pytest.raises(ValidationError) as exc_info:
        validate_status_field("all")

    assert exc_info.value.code == "INVALID_TASK_STATUS"
    assert exc_info.value.message == "Task status is invalid."
    assert exc_info.value.details["status"] == "all"
    assert exc_info.value.details["allowed_statuses"] == sorted(VALID_TASK_STATUSES - {"all"})


def test_validate_status_field_invalid_unknown():
    """Test that an unknown status is invalid."""
    with pytest.raises(ValidationError) as exc_info:
        validate_status_field("unknown-status")

    assert exc_info.value.code == "INVALID_TASK_STATUS"
    assert exc_info.value.message == "Task status is invalid."
    assert exc_info.value.details["status"] == "unknown-status"
    assert exc_info.value.details["allowed_statuses"] == sorted(VALID_TASK_STATUSES - {"all"})


def test_validate_status_field_invalid_empty():
    """Test that an empty status is invalid."""
    with pytest.raises(ValidationError) as exc_info:
        validate_status_field("")

    assert exc_info.value.code == "INVALID_TASK_STATUS"
    assert exc_info.value.message == "Task status is invalid."
    assert exc_info.value.details["status"] == ""
    assert exc_info.value.details["allowed_statuses"] == sorted(VALID_TASK_STATUSES - {"all"})
