"""Tests for low-level SQL helpers in phase_persistence."""

from engram.db import get_db_connection
from engram.models.phase_persistence import (
    fetch_phase_row,
    fetch_project_phase_rows,
    insert_phase,
    resolve_next_order_index,
    update_phase_fields,
)


def test_resolve_next_order_index_empty(tmp_db, project):
    """Test resolve_next_order_index on a project with no phases."""
    conn = get_db_connection()
    try:
        assert resolve_next_order_index(conn, project.id) == 0
    finally:
        conn.close()


def test_resolve_next_order_index_existing(tmp_db, project):
    """Test resolve_next_order_index returns max + 1."""
    conn = get_db_connection()
    try:
        insert_phase(
            conn,
            phase_id="phase-1",
            project_id=project.id,
            title="P1",
            description=None,
            status="planned",
            order_index=0,
            acceptance=None,
            evidence=None,
        )
        insert_phase(
            conn,
            phase_id="phase-2",
            project_id=project.id,
            title="P2",
            description=None,
            status="planned",
            order_index=5,
            acceptance=None,
            evidence=None,
        )
        conn.commit()
        assert resolve_next_order_index(conn, project.id) == 6
    finally:
        conn.close()


def test_insert_and_fetch_phase_row(tmp_db, project):
    """Test insert_phase and fetch_phase_row work correctly."""
    conn = get_db_connection()
    try:
        insert_phase(
            conn,
            phase_id="phase-test",
            project_id=project.id,
            title="Test Phase",
            description="Test Desc",
            status="active",
            order_index=1,
            acceptance="Tests pass",
            evidence="Done",
        )
        conn.commit()

        row = fetch_phase_row(conn, "phase-test")
        assert row is not None
        assert row["id"] == "phase-test"
        assert row["project_id"] == project.id
        assert row["title"] == "Test Phase"
        assert row["description"] == "Test Desc"
        assert row["status"] == "active"
        assert row["order_index"] == 1
        assert row["acceptance"] == "Tests pass"
        assert row["evidence"] == "Done"
    finally:
        conn.close()


def test_fetch_phase_row_non_existent(tmp_db):
    """Test fetch_phase_row with a missing ID returns None."""
    conn = get_db_connection()
    try:
        row = fetch_phase_row(conn, "does-not-exist")
        assert row is None
    finally:
        conn.close()


def test_fetch_project_phase_rows(tmp_db, project):
    """Test fetch_project_phase_rows returns rows ordered by order_index, created_at."""
    conn = get_db_connection()
    try:
        # Insert out of order
        insert_phase(
            conn,
            phase_id="p-2",
            project_id=project.id,
            title="P2",
            description=None,
            status="planned",
            order_index=2,
            acceptance=None,
            evidence=None,
        )
        insert_phase(
            conn,
            phase_id="p-1",
            project_id=project.id,
            title="P1",
            description=None,
            status="planned",
            order_index=0,
            acceptance=None,
            evidence=None,
        )
        insert_phase(
            conn,
            phase_id="p-3",
            project_id=project.id,
            title="P3",
            description=None,
            status="planned",
            order_index=1,
            acceptance=None,
            evidence=None,
        )
        conn.commit()

        rows = fetch_project_phase_rows(conn, project.id)
        assert len(rows) == 3
        # Should be ordered by order_index ASC
        assert rows[0]["id"] == "p-1"
        assert rows[1]["id"] == "p-3"
        assert rows[2]["id"] == "p-2"
    finally:
        conn.close()


def test_update_phase_fields(tmp_db, project):
    """Test update_phase_fields updates only specified fields."""
    conn = get_db_connection()
    try:
        insert_phase(
            conn,
            phase_id="p-upd",
            project_id=project.id,
            title="Old Title",
            description=None,
            status="planned",
            order_index=0,
            acceptance=None,
            evidence=None,
        )
        conn.commit()

        # Update title and status
        update_phase_fields(conn, "p-upd", {"title": "New Title", "status": "active"})
        conn.commit()

        row = fetch_phase_row(conn, "p-upd")
        assert row["title"] == "New Title"
        assert row["status"] == "active"
        assert row["order_index"] == 0  # Unchanged
        assert row["description"] is None  # Unchanged
    finally:
        conn.close()


def test_update_phase_fields_empty(tmp_db, project):
    """Test update_phase_fields does nothing if updates dict is empty."""
    conn = get_db_connection()
    try:
        insert_phase(
            conn,
            phase_id="p-empty",
            project_id=project.id,
            title="Title",
            description=None,
            status="planned",
            order_index=0,
            acceptance=None,
            evidence=None,
        )
        conn.commit()

        # Empty updates
        update_phase_fields(conn, "p-empty", {})
        conn.commit()

        row = fetch_phase_row(conn, "p-empty")
        assert row["title"] == "Title"  # Unchanged
    finally:
        conn.close()
