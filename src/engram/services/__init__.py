"""Service-layer contracts shared by CLI and MCP adapters."""

from engram.services.errors import EngramServiceError
from engram.services.memory_service import search_memories
from engram.services.project_service import resolve_current_project
from engram.services.serializers import memory_to_dict, phase_to_dict, project_to_dict, task_to_dict
from engram.services.task_service import get_task, list_tasks, resolve_task_ref

__all__ = [
    "EngramServiceError",
    "resolve_current_project",
    "search_memories",
    "resolve_task_ref",
    "list_tasks",
    "get_task",
    "project_to_dict",
    "task_to_dict",
    "memory_to_dict",
    "phase_to_dict",
]
