"""Tests for service-layer JSON-safe serializers."""

from __future__ import annotations

from typing import Any

import engram.services.serializers as serializers
from engram.models.memory import Memory
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task
from engram.services.serializers import memory_to_dict, phase_to_dict, project_to_dict, task_to_dict


def _assert_json_safe(value: Any) -> None:
    if value is None or isinstance(value, str | int | float | bool):
        return
    if isinstance(value, list):
        for item in value:
            _assert_json_safe(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str)
            _assert_json_safe(item)
        return
    raise AssertionError(f"Non JSON-safe value encountered: {type(value)!r}")


def test_project_to_dict_shape_and_missing_optional_values():
    project = Project(
        "proj1234", "Engram", summary=" ", status="active", repo_paths=["D:/repo/engram"]
    )

    payload = project_to_dict(project)

    assert payload == {
        "id": "proj1234",
        "plan_key": "proj1234",
        "name": "Engram",
        "summary": None,
        "status": "active",
        "repo_paths": ["D:/repo/engram"],
    }
    _assert_json_safe(payload)


def test_task_to_dict_shape_lists_optional_values_and_effective_status(monkeypatch):
    dependency = Task("dep12345", "proj1234", "Dependency task", status="todo", priority="medium")
    task = Task(
        id="task1234",
        project_id="proj1234",
        title="Implement serializers",
        description=" ",
        status="todo",
        priority="high",
        phase=" ",
        phase_id=None,
        depends_on="dep12345",
        acceptance=None,
        evidence=None,
        tags=["mcp", "services"],
        relevant_files=["src/engram/services/serializers.py"],
    )

    dependencies = {dependency.id: dependency}
    monkeypatch.setattr(
        serializers.Task, "get", classmethod(lambda cls, dep_id: dependencies.get(dep_id))
    )
    payload = task_to_dict(task)

    assert payload == {
        "id": "task1234",
        "project_id": "proj1234",
        "key": "task1234",
        "title": "Implement serializers",
        "description": None,
        "objective": None,
        "status": "todo",
        "effective_status": "blocked",
        "priority": "high",
        "phase": None,
        "phase_id": None,
        "phase_key": None,
        "phase_title": None,
        "depends_on": "dep12345",
        "acceptance": None,
        "evidence": None,
        "tags": ["mcp", "services"],
        "relevant_files": ["src/engram/services/serializers.py"],
        "verification": None,
        "search_hints": [],
        "memory_review_outcome": None,
        "is_verified": False,
    }
    _assert_json_safe(payload)


def test_task_to_dict_compact_shape_omits_descriptions(monkeypatch):
    phase = Phase(
        id="phase1234",
        project_id="proj1234",
        title="Phase Title",
        status="active",
        order_index=1,
        key="phase-key",
    )
    monkeypatch.setattr(
        serializers.Phase,
        "get",
        classmethod(lambda cls, phase_id: phase if phase_id == "phase1234" else None),
    )
    task = Task(
        id="task1234",
        project_id="proj1234",
        title="Implement serializers",
        description="Task details",
        status="in_progress",
        priority="high",
        phase="Phase Title",
        phase_id="phase1234",
        is_verified=True,
    )

    payload = task_to_dict(task, compact=True)

    assert payload == {
        "id": "task1234",
        "key": "task1234",
        "title": "Implement serializers",
        "status": "in_progress",
        "phase_id": "phase1234",
        "phase_key": "phase-key",
        "phase_title": "Phase Title",
        "is_verified": True,
    }
    _assert_json_safe(payload)


def test_task_to_dict_with_memory_review_outcome(monkeypatch):
    task = Task(
        id="task1234",
        project_id="proj1234",
        title="Implement serializers",
        status="done",
        priority="high",
        memory_review_outcome="created",
    )
    payload = task_to_dict(task)
    assert payload["memory_review_outcome"] == "created"
    _assert_json_safe(payload)


def test_memory_to_dict_shape_and_optional_values():
    memory = Memory(
        id="mem12345",
        project_id="proj1234",
        type="note",
        title="Temp note",
        content="Body",
        scope="task",
        task_id=" ",
        tags=["mcp"],
        always_include=1,
        level=None,
    )

    payload = memory_to_dict(memory)

    assert payload == {
        "id": "mem12345",
        "project_id": "proj1234",
        "type": "note",
        "title": "Temp note",
        "content": "Body",
        "scope": "task",
        "task_id": None,
        "tags": ["mcp"],
        "always_include": True,
        "level": None,
        "superseded_by": None,
    }
    _assert_json_safe(payload)


def test_phase_to_dict_shape_and_missing_optional_values():
    phase = Phase(
        id="phase123",
        project_id="proj1234",
        title="MCP - Phase 1",
        description=" ",
        status="planned",
        order_index=2,
        acceptance=None,
        evidence=" ",
    )

    payload = phase_to_dict(phase)

    assert payload == {
        "id": "phase123",
        "project_id": "proj1234",
        "key": "phase123",
        "title": "MCP - Phase 1",
        "description": None,
        "status": "planned",
        "order_index": 2,
        "acceptance": None,
        "evidence": None,
    }
    _assert_json_safe(payload)


def test_phase_to_dict_includes_review_pending_status_label():
    phase = Phase(
        id="phase124",
        project_id="proj1234",
        title="MCP - Phase 2",
        status="review_pending",
        order_index=3,
    )

    payload = phase_to_dict(phase)

    assert payload == {
        "id": "phase124",
        "project_id": "proj1234",
        "key": "phase124",
        "title": "MCP - Phase 2",
        "description": None,
        "status": "review_pending",
        "order_index": 3,
        "acceptance": None,
        "evidence": None,
        "status_label": "To be reviewed",
    }
    _assert_json_safe(payload)


def test_phase_to_dict_supports_compact_and_marker_fields():
    phase = Phase(
        id="phase125",
        project_id="proj1234",
        title="MCP - Phase 3",
        status="active",
        order_index=4,
    )

    payload = phase_to_dict(
        phase,
        compact=True,
        markers={"current": True, "review_candidate": False, "next_planned": False},
    )

    assert payload == {
        "id": "phase125",
        "key": "phase125",
        "title": "MCP - Phase 3",
        "status": "active",
        "current": True,
        "review_candidate": False,
        "next_planned": False,
    }
    _assert_json_safe(payload)
