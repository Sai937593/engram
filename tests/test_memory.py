"""Tests for Memory model including FTS5 search."""
import pytest
from engram.models.memory import Memory


def test_create_memory(project):
    m = Memory.create(
        project_id=project.id,
        type="decision",
        title="Use SQLite",
        content="SQLite is ideal for local-first apps.",
        tags=["storage", "arch"],
    )
    assert m.title == "Use SQLite"
    assert m.type == "decision"
    assert "storage" in m.tags
    assert m.always_include is False


def test_create_memory_always_include(project):
    m = Memory.create(
        project_id=project.id,
        type="constraint",
        title="No production writes",
        content="Never write to production DB directly.",
        always_include=True,
    )
    assert m.always_include is True


def test_get_memory(memory):
    fetched = Memory.get(memory.id)
    assert fetched is not None
    assert fetched.title == memory.title


def test_get_nonexistent_memory(tmp_db):
    assert Memory.get("no-such-id") is None


def test_list_by_project(project):
    Memory.create(project_id=project.id, type="note", title="Note A", content="...")
    Memory.create(project_id=project.id, type="lesson", title="Lesson B", content="...")
    memories = Memory.list_by_project(project.id)
    titles = [m.title for m in memories]
    assert "Note A" in titles
    assert "Lesson B" in titles


def test_list_always_include(project):
    Memory.create(project_id=project.id, type="constraint", title="Always", content="x", always_include=True)
    Memory.create(project_id=project.id, type="note", title="Not always", content="y", always_include=False)
    results = Memory.list_always_include(project.id)
    assert len(results) == 1
    assert results[0].title == "Always"


def test_update_memory_content(memory):
    memory.update(content="Updated content here.")
    refreshed = Memory.get(memory.id)
    assert refreshed.content == "Updated content here."


def test_update_memory_tags(memory):
    memory.update(tags=["new-tag", "another"])
    refreshed = Memory.get(memory.id)
    assert "new-tag" in refreshed.tags


def test_update_memory_always_include(memory):
    memory.update(always_include=True)
    refreshed = Memory.get(memory.id)
    assert refreshed.always_include is True


def test_delete_memory(memory):
    memory.delete()
    assert Memory.get(memory.id) is None


def test_fts_search(project):
    Memory.create(project_id=project.id, type="lesson", title="WAL mode", content="WAL mode needed for concurrent reads in SQLite.")
    Memory.create(project_id=project.id, type="note", title="Unrelated", content="Something completely different.")
    results = Memory.search("WAL concurrent")
    titles = [m.title for m in results]
    assert "WAL mode" in titles
