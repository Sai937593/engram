import pytest
from pydantic import ValidationError

from engram.mcp.schemas import ToolCall


def test_tool_call_valid_creation():
    """Test creating a ToolCall with valid data."""
    data = {"name": "test_tool", "arguments": {"arg1": "value1", "arg2": 2}}
    tool_call = ToolCall(**data)
    assert tool_call.name == "test_tool"
    assert tool_call.arguments == {"arg1": "value1", "arg2": 2}


def test_tool_call_missing_required_fields():
    """Test that missing required fields raises a ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        ToolCall()

    errors = exc_info.value.errors()
    assert len(errors) == 2
    assert errors[0]["loc"] == ("name",)
    assert errors[0]["type"] == "missing"
    assert errors[1]["loc"] == ("arguments",)
    assert errors[1]["type"] == "missing"


def test_tool_call_invalid_name_type():
    """Test that an invalid type for 'name' raises a ValidationError."""
    # Pydantic often attempts to coerce types (e.g., int to str),
    # but a dictionary cannot be coerced to a string normally.
    data = {"name": {"invalid": "type"}, "arguments": {"arg1": "value1"}}
    with pytest.raises(ValidationError) as exc_info:
        ToolCall(**data)

    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("name",)
    assert errors[0]["type"] == "string_type"


def test_tool_call_invalid_arguments_type():
    """Test that an invalid type for 'arguments' raises a ValidationError."""
    data = {"name": "test_tool", "arguments": ["this", "is", "a", "list"]}
    with pytest.raises(ValidationError) as exc_info:
        ToolCall(**data)

    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("arguments",)
    assert errors[0]["type"] == "dict_type"
