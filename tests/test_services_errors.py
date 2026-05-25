"""Tests for service-safe errors."""

from engram.services.errors import EngramServiceError


class _DebugObject:
    def __str__(self) -> str:
        return "debug-object"


def test_engram_service_error_defaults_details_to_empty_dict():
    error = EngramServiceError(code="task_not_found", message="Task was not found.")

    assert error.code == "task_not_found"
    assert error.message == "Task was not found."
    assert error.details == {}
    assert error.to_dict() == {
        "code": "task_not_found",
        "message": "Task was not found.",
        "details": {},
    }


def test_engram_service_error_preserves_explicit_details_and_normalizes_json_shapes():
    details = {
        "task_id": "tsk1234",
        "retry_count": 2,
        "metadata": {"phase": "phase-1", "active": True},
        "labels": ["mcp", "services"],
        "extra": _DebugObject(),
    }
    error = EngramServiceError(
        code="dependency_failure",
        message="Could not resolve task dependency.",
        details=details,
    )

    payload = error.to_dict()
    assert payload["code"] == "dependency_failure"
    assert payload["message"] == "Could not resolve task dependency."
    assert payload["details"] == {
        "task_id": "tsk1234",
        "retry_count": 2,
        "metadata": {"phase": "phase-1", "active": True},
        "labels": ["mcp", "services"],
        "extra": "debug-object",
    }
