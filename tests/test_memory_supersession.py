import pytest

from engram.db import get_db_connection, init_db
from engram.memory_retrieval.fts_retriever.retriever import _fetch_task_memory_fts_rows
from engram.memory_retrieval.fts_retriever.scoring import _is_semantic_eligible
from engram.models.audit import AuditLog
from engram.models.memory import Memory
from engram.services.memory_service import create_memory, list_memories, search_memories


def test_schema_and_migration(tmp_db):
    """Test that schema migration runs idempotently and superseded_by exists."""
    conn = get_db_connection(tmp_db)
    cursor = conn.cursor()

    # Check that superseded_by column exists
    rows = cursor.execute("PRAGMA table_info(memories)").fetchall()
    column_names = [row["name"] for row in rows]
    assert "superseded_by" in column_names

    # Run init_db again to verify idempotence
    init_db(tmp_db)

    # Verify column still exists
    rows = cursor.execute("PRAGMA table_info(memories)").fetchall()
    column_names = [row["name"] for row in rows]
    assert "superseded_by" in column_names
    conn.close()


def test_memory_creation_and_linking(project):
    """Test standard memory creation and supersession linking with audit log checks."""
    # 1. Create a base memory
    m1 = Memory.create(
        project_id=project.id,
        type="lesson",
        title="Old Way of Doing Things",
        content="This is the old outdated guide.",
        scope="project",
        level="L1",
    )
    assert m1.id is not None
    assert m1.superseded_by is None

    # Verify audit log for creation
    logs = AuditLog.get_logs_for_target("memories", m1.id)
    assert len(logs) == 1
    assert logs[0]["operation"] == "create"

    # 2. Create a new memory superseding the base one
    m2 = Memory.create(
        project_id=project.id,
        type="lesson",
        title="New Way of Doing Things",
        content="This is the new modern guide.",
        scope="project",
        level="L1",
        supersedes=m1.id,
    )
    assert m2.id is not None
    assert m2.superseded_by is None

    # 3. Reload m1 and verify superseded_by is linked to m2
    m1_reloaded = Memory.get(m1.id)
    assert m1_reloaded is not None
    assert m1_reloaded.superseded_by == m2.id

    # Verify audit logs for m1 are updated and logged
    logs_m1 = AuditLog.get_logs_for_target("memories", m1.id)
    assert len(logs_m1) >= 2
    # One of the logs must be the update of superseded_by
    update_logs = [
        log for log in logs_m1 if log["operation"] == "update" and log["field"] == "superseded_by"
    ]
    assert len(update_logs) == 1
    assert update_logs[0]["new_value"] == m2.id

    # Verify invalid supersedes reference raises ValueError
    with pytest.raises(ValueError) as excinfo:
        Memory.create(
            project_id=project.id,
            type="lesson",
            title="Another New Memory",
            content="Some content",
            scope="project",
            level="L1",
            supersedes="non-existent-id",
        )
    assert "to supersede not found" in str(excinfo.value)


def test_superseded_memory_retrieval_filtering(project):
    """Test that standard searches and lists filter out superseded memories by default."""
    m1 = Memory.create(
        project_id=project.id,
        type="lesson",
        title="Old Outdated Guide",
        content="Avoid this outdated instruction.",
        scope="project",
        level="L1",
    )
    m2 = Memory.create(
        project_id=project.id,
        type="lesson",
        title="New Modern Guide",
        content="Follow this modern instruction.",
        scope="project",
        level="L1",
        supersedes=m1.id,
    )

    # 1. Test search() method
    # Default search: filters out superseded memory (m1)
    results = Memory.search("instruction", project_id=project.id)
    assert len(results) == 1
    assert results[0].id == m2.id

    # Search with include_superseded=True: returns both
    results_all = Memory.search("instruction", project_id=project.id, include_superseded=True)
    assert len(results_all) == 2
    ids = {r.id for r in results_all}
    assert ids == {m1.id, m2.id}

    # 2. Test list_by_project()
    assert len(Memory.list_by_project(project.id)) == 1
    assert len(Memory.list_by_project(project.id, include_superseded=True)) == 2

    # 3. Test list_by_type()
    assert len(Memory.list_by_type(project.id, "lesson")) == 1
    assert len(Memory.list_by_type(project.id, "lesson", include_superseded=True)) == 2

    # 4. Test list_project_guardrail_candidates()
    assert len(Memory.list_project_guardrail_candidates(project.id)) == 1
    assert len(Memory.list_project_guardrail_candidates(project.id, include_superseded=True)) == 2


def test_retrieval_and_scoring_eligibility(project):
    """Test that FTS candidates fetch and semantic eligibility skip superseded memories."""
    m1 = Memory.create(
        project_id=project.id,
        type="lesson",
        title="FTS Target Old",
        content="Search keyword apple pie recipe.",
        scope="project",
        level="L2",
    )
    m2 = Memory.create(
        project_id=project.id,
        type="lesson",
        title="FTS Target New",
        content="Search keyword apple pie recipe modern.",
        scope="project",
        level="L2",
        supersedes=m1.id,
    )

    # Verify FTS rows fetching filters out m1
    from engram.memory_retrieval.fts_query import normalize_fts_query_text

    safe_query = normalize_fts_query_text("apple pie")
    fts_rows = _fetch_task_memory_fts_rows(
        project_id=project.id, safe_fts_query=safe_query, max_candidates=10
    )
    assert len(fts_rows) == 1
    assert fts_rows[0].memory_id == m2.id

    # Verify semantic eligibility checks superseded attribute
    m1_reloaded = Memory.get(m1.id)
    assert _is_semantic_eligible(m2) is True
    assert _is_semantic_eligible(m1_reloaded) is False  # Omitted because it has superseded_by set


def test_service_layer_integration(project):
    """Test memory supersession through memory_service functions."""
    m1_dto = create_memory(
        project_id=project.id,
        type="lesson",
        title="Old Service Memory",
        content="Content old",
        scope="project",
        level="L1",
    )

    m2_dto = create_memory(
        project_id=project.id,
        type="lesson",
        title="New Service Memory",
        content="Content new",
        scope="project",
        level="L1",
        supersedes=m1_dto["id"],
    )

    assert m2_dto["superseded_by"] is None

    # Reload m1 through list_memories and verify it includes superseded_by
    m1_reloaded_list = list_memories(project.id, include_superseded=True)
    m1_dto_reloaded = next(m for m in m1_reloaded_list if m["id"] == m1_dto["id"])
    assert m1_dto_reloaded["superseded_by"] == m2_dto["id"]

    # Verify default list does not include superseded memory
    active_memories = list_memories(project.id)
    assert len(active_memories) == 1
    assert active_memories[0]["id"] == m2_dto["id"]

    # Verify default search does not include superseded memory
    searched = search_memories(project.id, "Content")
    assert len(searched) == 1
    assert searched[0]["id"] == m2_dto["id"]
