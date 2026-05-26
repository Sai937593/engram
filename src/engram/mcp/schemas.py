"""Schema placeholders for future MCP resources and tools."""

from typing import Any
from pydantic import BaseModel

RESOURCE_SCHEMAS: dict[str, dict[str, object]] = {}
TOOL_SCHEMAS: dict[str, dict[str, object]] = {}

class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]
