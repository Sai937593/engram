"""Service-layer contracts shared by CLI and MCP adapters."""

from engram.services.errors import EngramServiceError
from engram.services.serializers import memory_to_dict, phase_to_dict, project_to_dict, task_to_dict

__all__ = [
    "EngramServiceError",
    "project_to_dict",
    "task_to_dict",
    "memory_to_dict",
    "phase_to_dict",
]
