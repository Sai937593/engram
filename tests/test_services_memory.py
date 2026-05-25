"""Tests for memory service read boundaries."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from engram.db import get_db_connection
from engram.models.memory import Memory
from engram.models.project import Project
from engram.services.errors import EngramServiceError
from engram.services.memory_service import list_memories, search_memories


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
