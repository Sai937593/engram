"""Tests for memory service read boundaries."""

from __future__ import annotations

import ast
import importlib
import time
from pathlib import Path

import pytest

from engram.db import get_db_connection
from engram.models.memory import Memory
from engram.models.project import Project
from engram.services.errors import EngramServiceError, ValidationError
from engram.services.memory_service import (
    create_memory,
    get_recent_memories,
    list_memories,
    search_memories,
)


def _create_project(project_id: str, repo_path: str) -> Project:
    return Project.create(
        id=project_id,
        name=f"Project {project_id}",
        summary="Memory service tests",
        repo_paths=[repo_path],
    )


def _memory_rows(project_id: str) -> list[dict[str, object]]:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM memories WHERE project_id = ? ORDER BY id ASC",
        (project_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def test_search_memories_returns_project_scoped_json_safe_payloads(tmp_db):
    target_project = _create_project("proj-mem-a", "/tmp/proj-mem-a")
    foreign_project = _create_project("proj-mem-b", "/tmp/proj-mem-b")
    Memory.create(
        project_id=target_project.id,
        id="mema0001",
        type="lesson",
        title="SQLite FTS behavior",
        content="SQLite FTS query handling for memory service.",
        tags=["sqlite", "fts"],
        level="L3",
    )
    Memory.create(
        project_id=foreign_project.id,
        id="memb0001",
        type="lesson",
        title="Foreign SQLite lesson",
        content="SQLite FTS query handling for another project.",
        tags=["sqlite", "fts"],
        level="L3",
    )

    payloads = search_memories(target_project.id, query="SQLite FTS", limit=10)

    assert [payload["id"] for payload in payloads] == ["mema0001"]
    assert payloads[0]["project_id"] == target_project.id
    assert payloads[0]["type"] == "lesson"
    assert isinstance(payloads[0]["always_include"], bool)
    assert isinstance(payloads[0]["tags"], list)


def test_list_memories_returns_project_scoped_json_safe_payloads(tmp_db):
    target_project = _create_project("proj-list-a", "/tmp/proj-list-a")
    foreign_project = _create_project("proj-list-b", "/tmp/proj-list-b")
    Memory.create(
        project_id=target_project.id,
        id="lsta0001",
        type="lesson",
        title="Target lesson",
        content="Belongs to target project.",
        tags=["target"],
        level="L3",
    )
    Memory.create(
        project_id=target_project.id,
        id="lsta0002",
        type="note",
        title="Target note",
        content="Second target memory.",
        tags=["target"],
        level="L3",
    )
    Memory.create(
        project_id=foreign_project.id,
        id="lstb0001",
        type="lesson",
        title="Foreign lesson",
        content="Belongs to foreign project.",
        tags=["foreign"],
        level="L3",
    )

    payloads = list_memories(target_project.id)

    assert [payload["id"] for payload in payloads] == ["lsta0001", "lsta0002"]
    assert all(payload["project_id"] == target_project.id for payload in payloads)
    assert isinstance(payloads[0]["always_include"], bool)
    assert isinstance(payloads[0]["tags"], list)


def test_list_memories_applies_type_filter(tmp_db):
    project = _create_project("proj-list-c", "/tmp/proj-list-c")
    Memory.create(
        project_id=project.id,
        id="lstc0001",
        type="lesson",
        title="Lesson memory",
        content="Service filtering lesson",
        level="L3",
    )
    Memory.create(
        project_id=project.id,
        id="lstc0002",
        type="note",
        title="Note memory",
        content="Service filtering note",
        level="L3",
    )

    payloads = list_memories(project.id, type_filter="lesson")

    assert [payload["id"] for payload in payloads] == ["lstc0001"]
    assert all(payload["type"] == "lesson" for payload in payloads)


def test_list_memories_limit_none_returns_all_matching_rows(tmp_db):
    project = _create_project("proj-list-d", "/tmp/proj-list-d")
    for index in range(3):
        Memory.create(
            project_id=project.id,
            id=f"lstd{index:04d}",
            type="note",
            title=f"List note {index}",
            content="List all rows with no limit.",
            level="L3",
        )

    payloads = list_memories(project.id, type_filter="note", limit=None)

    assert [payload["id"] for payload in payloads] == ["lstd0000", "lstd0001", "lstd0002"]


def test_list_memories_positive_limit_caps_results_deterministically(tmp_db):
    project = _create_project("proj-list-e", "/tmp/proj-list-e")
    for index in range(4):
        Memory.create(
            project_id=project.id,
            id=f"lste{index:04d}",
            type="note",
            title=f"Deterministic note {index}",
            content="Deterministic ordering check.",
            level="L3",
        )

    payloads = list_memories(project.id, limit=2)

    assert [payload["id"] for payload in payloads] == ["lste0000", "lste0001"]


def test_search_memories_returns_empty_list_for_no_matches(tmp_db):
    project = _create_project("proj-mem-c", "/tmp/proj-mem-c")
    Memory.create(
        project_id=project.id,
        id="memc0001",
        type="note",
        title="Unrelated",
        content="No overlap with search query text.",
        tags=["misc"],
        level="L3",
    )

    payloads = search_memories(project.id, query="postgres replication failover")

    assert payloads == []


def test_search_memories_defaults_limit_to_ten(tmp_db):
    project = _create_project("proj-mem-d", "/tmp/proj-mem-d")
    for index in range(11):
        Memory.create(
            project_id=project.id,
            id=f"memd{index:04d}",
            type="note",
            title=f"Starter note {index}",
            content="startup retrieval behavior note",
            tags=["startup"],
            level="L3",
        )

    payloads = search_memories(project.id, query="startup retrieval")

    assert len(payloads) == 10


def test_search_memories_passes_type_and_tag_filters_through_existing_model_behavior(tmp_db):
    project = _create_project("proj-mem-e", "/tmp/proj-mem-e")
    Memory.create(
        project_id=project.id,
        id="meme0001",
        type="lesson",
        title="WAL lesson",
        content="WAL mode notes for startup",
        tags=["db", "wal"],
        level="L3",
    )
    Memory.create(
        project_id=project.id,
        id="meme0002",
        type="note",
        title="WAL note",
        content="WAL mode notes for startup",
        tags=["db", "wal"],
        level="L3",
    )
    Memory.create(
        project_id=project.id,
        id="meme0003",
        type="lesson",
        title="WAL lesson no tag",
        content="WAL mode notes for startup",
        tags=["db"],
        level="L3",
    )

    payloads = search_memories(
        project.id,
        query="WAL startup",
        type_filter="lesson",
        tags=["wal"],
        limit=10,
    )

    assert [payload["id"] for payload in payloads] == ["meme0001"]


@pytest.mark.parametrize("invalid_limit", [0, -1, -99])
def test_search_memories_raises_validation_error_for_non_positive_limit(tmp_db, invalid_limit):
    project = _create_project("proj-mem-f", "/tmp/proj-mem-f")
    Memory.create(
        project_id=project.id,
        id="memf0001",
        type="note",
        title="Any note",
        content="Any content",
        level="L3",
    )

    with pytest.raises(EngramServiceError) as raised:
        search_memories(project.id, query="Any", limit=invalid_limit)

    error = raised.value
    assert error.code == "VALIDATION_ERROR"
    assert error.message == "Limit must be a positive integer."
    assert error.details == {"field": "limit", "value": invalid_limit}


@pytest.mark.parametrize("invalid_limit", [0, -1, -99])
def test_list_memories_raises_validation_error_for_non_positive_limit(tmp_db, invalid_limit):
    project = _create_project("proj-list-f", "/tmp/proj-list-f")
    Memory.create(
        project_id=project.id,
        id="lstf0001",
        type="note",
        title="Any note",
        content="Any content",
        level="L3",
    )

    with pytest.raises(EngramServiceError) as raised:
        list_memories(project.id, limit=invalid_limit)

    error = raised.value
    assert error.code == "VALIDATION_ERROR"
    assert error.message == "Limit must be a positive integer."
    assert error.details == {"field": "limit", "value": invalid_limit}


def test_memory_service_module_is_adapter_safe(tmp_db):
    module = importlib.import_module("engram.services.memory_service")
    source = Path(module.__file__).read_text(encoding="utf-8")
    parsed = ast.parse(source)
    banned_prefixes = ("click", "rich", "engram.cli", "engram.mcp", "subprocess")

    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(banned_prefixes)
        elif isinstance(node, ast.ImportFrom):
            imported_module = node.module or ""
            assert not imported_module.startswith(banned_prefixes)


def test_search_memories_calls_are_read_only_on_memory_rows(tmp_db):
    project = _create_project("proj-mem-g", "/tmp/proj-mem-g")
    Memory.create(
        project_id=project.id,
        id="memg0001",
        type="lesson",
        title="Read-only target",
        content="Read only behavior check",
        tags=["read"],
        level="L3",
    )
    before_rows = _memory_rows(project.id)

    search_memories(project.id, query="read only", limit=5)
    search_memories(project.id, query="read only", type_filter="lesson", tags=["read"], limit=1)
    list_memories(project.id)
    list_memories(project.id, type_filter="lesson", limit=1)

    after_rows = _memory_rows(project.id)
    assert after_rows == before_rows


def test_create_memory_happy_path_project_scope(tmp_db):
    project = _create_project("proj-create-a", "/tmp/proj-create-a")
    dto = create_memory(
        project_id=project.id,
        type="lesson",
        title="Valid lesson title",
        content="Valid lesson content",
        scope="project",
        level="L2",
        tags=["foo", "bar"],
    )

    assert dto["project_id"] == project.id
    assert dto["type"] == "lesson"
    assert dto["title"] == "Valid lesson title"
    assert dto["content"] == "Valid lesson content"
    assert dto["scope"] == "project"
    assert dto["level"] == "L2"
    assert dto["tags"] == ["foo", "bar"]
    assert dto["always_include"] is False
    assert len(dto["id"]) == 8

    # Fetch from db to verify it's persisted
    fetched = Memory.get(dto["id"])
    assert fetched is not None
    assert fetched.title == "Valid lesson title"


def test_create_memory_happy_path_task_scope(tmp_db):
    project = _create_project("proj-create-b", "/tmp/proj-create-b")
    dto = create_memory(
        project_id=project.id,
        type="note",
        title="Valid note title",
        content="Valid note content",
        scope="task",
        task_id="task0001",
        level=None,
    )

    assert dto["project_id"] == project.id
    assert dto["type"] == "note"
    assert dto["scope"] == "task"
    assert dto["task_id"] == "task0001"
    assert dto["level"] is None

    fetched = Memory.get(dto["id"])
    assert fetched is not None
    assert fetched.scope == "task"


def test_create_memory_invalid_type_raises_validation_error(tmp_db):
    project = _create_project("proj-create-c", "/tmp/proj-create-c")
    with pytest.raises(ValidationError) as exc:
        create_memory(
            project_id=project.id,
            type="invalid_type",
            title="Title",
            content="Content",
            scope="project",
            level="L1",
        )
    assert exc.value.code == "INVALID_MEMORY_TYPE"
    assert "type" in exc.value.details


def test_create_memory_invalid_scope_raises_validation_error(tmp_db):
    project = _create_project("proj-create-d", "/tmp/proj-create-d")
    with pytest.raises(ValidationError) as exc:
        create_memory(
            project_id=project.id,
            type="lesson",
            title="Title",
            content="Content",
            scope="invalid_scope",
            level="L1",
        )
    assert exc.value.code == "INVALID_MEMORY_SCOPE"
    assert "scope" in exc.value.details


def test_create_memory_project_scope_without_level_raises_validation_error(tmp_db):
    project = _create_project("proj-create-e", "/tmp/proj-create-e")
    # Empty level
    with pytest.raises(ValidationError) as exc:
        create_memory(
            project_id=project.id,
            type="lesson",
            title="Title",
            content="Content",
            scope="project",
            level=None,
        )
    assert exc.value.code == "INVALID_MEMORY_LEVEL"

    # Invalid level
    with pytest.raises(ValidationError) as exc:
        create_memory(
            project_id=project.id,
            type="lesson",
            title="Title",
            content="Content",
            scope="project",
            level="L5",
        )
    assert exc.value.code == "INVALID_MEMORY_LEVEL"


def test_create_memory_task_scope_with_level_raises_validation_error(tmp_db):
    project = _create_project("proj-create-f", "/tmp/proj-create-f")
    with pytest.raises(ValidationError) as exc:
        create_memory(
            project_id=project.id,
            type="note",
            title="Title",
            content="Content",
            scope="task",
            level="L1",
        )
    assert exc.value.code == "INVALID_MEMORY_LEVEL"


@pytest.mark.slow
def test_get_recent_memories_returns_correct_order(tmp_db):
    project = _create_project("proj-recent-a", "/tmp/proj-recent-a")
    Memory.create(
        project_id=project.id,
        id="reca0001",
        type="lesson",
        title="Oldest memory",
        content="This is the oldest memory.",
        level="L3",
    )
    time.sleep(1)  # SQLite datetime('now') resolution is seconds
    Memory.create(
        project_id=project.id,
        id="reca0002",
        type="lesson",
        title="Newest memory",
        content="This is the newest memory.",
        level="L3",
    )

    memories = get_recent_memories(project_id=project.id)
    assert len(memories) == 2
    assert memories[0].id == "reca0002"
    assert memories[1].id == "reca0001"


def test_get_recent_memories_limits_to_requested(tmp_db):
    project = _create_project("proj-recent-b", "/tmp/proj-recent-b")
    for i in range(5):
        Memory.create(
            project_id=project.id,
            id=f"recb000{i}",
            type="note",
            title=f"Note {i}",
            content=f"Content {i}",
            level="L3",
        )

    memories = get_recent_memories(limit=3, project_id=project.id)
    assert len(memories) == 3


def test_get_recent_memories_caps_at_1000(tmp_db):
    project = _create_project("proj-recent-c", "/tmp/proj-recent-c")
    for i in range(3):
        Memory.create(
            project_id=project.id,
            id=f"recc000{i}",
            type="note",
            title=f"Note {i}",
            content=f"Content {i}",
            level="L3",
        )
    memories = get_recent_memories(limit=2000, project_id=project.id)
    assert len(memories) == 3


def test_get_recent_memories_filters_by_project_id(tmp_db):
    project1 = _create_project("proj-recent-d1", "/tmp/proj-recent-d1")
    project2 = _create_project("proj-recent-d2", "/tmp/proj-recent-d2")
    Memory.create(
        project_id=project1.id,
        id="recd0001",
        type="note",
        title="Note 1",
        content="Content 1",
        level="L3",
    )
    Memory.create(
        project_id=project2.id,
        id="recd0002",
        type="note",
        title="Note 2",
        content="Content 2",
        level="L3",
    )

    memories = get_recent_memories(project_id=project1.id)
    assert len(memories) == 1
    assert memories[0].id == "recd0001"


def test_get_recent_memories_no_project_id_returns_all(tmp_db):
    project1 = _create_project("proj-recent-e1", "/tmp/proj-recent-e1")
    project2 = _create_project("proj-recent-e2", "/tmp/proj-recent-e2")
    Memory.create(
        project_id=project1.id,
        id="rece0001",
        type="note",
        title="Note 1",
        content="Content 1",
        level="L3",
    )
    Memory.create(
        project_id=project2.id,
        id="rece0002",
        type="note",
        title="Note 2",
        content="Content 2",
        level="L3",
    )

    memories = get_recent_memories()
    assert len(memories) == 2
    assert {m.id for m in memories} == {"rece0001", "rece0002"}


@pytest.mark.parametrize("invalid_limit", [0, -1, -99])
def test_get_recent_memories_raises_validation_error_for_non_positive_limit(tmp_db, invalid_limit):
    with pytest.raises(EngramServiceError) as raised:
        get_recent_memories(limit=invalid_limit)
    error = raised.value
    assert error.code == "VALIDATION_ERROR"
    assert error.message == "Limit must be a positive integer."
    assert error.details == {"field": "limit", "value": invalid_limit}
