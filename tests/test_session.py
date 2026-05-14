"""Tests for Session model: create, close, checkpoint resumption."""
from engram.models.session import Session


def test_create_session(project):
    s = Session.create(project_id=project.id, goal="Build feature X")
    assert s.goal == "Build feature X"
    assert s.status == "open"
    assert s.closed_at is None


def test_get_active_session(project):
    Session.create(project_id=project.id, goal="Active goal")
    active = Session.get_active(project.id)
    assert active is not None
    assert active.goal == "Active goal"


def test_close_session(project):
    s = Session.create(project_id=project.id, goal="Close me")
    s.close(summary="Did the work", next_steps="Write more tests")
    refreshed = Session.get(s.id)
    assert refreshed.status == "closed"
    assert refreshed.summary == "Did the work"
    assert refreshed.next_steps == "Write more tests"
    assert refreshed.closed_at is not None


def test_get_latest_closed(project):
    s1 = Session.create(project_id=project.id, goal="First")
    s1.close(summary="First done")
    s2 = Session.create(project_id=project.id, goal="Second")
    s2.close(summary="Second done")
    latest = Session.get_latest_closed(project.id)
    assert latest.summary == "Second done"


def test_no_active_session_after_close(project):
    s = Session.create(project_id=project.id, goal="Will close")
    s.close(summary="Closed")
    assert Session.get_active(project.id) is None


def test_list_sessions(project):
    Session.create(project_id=project.id, goal="Session A")
    Session.create(project_id=project.id, goal="Session B")
    sessions = Session.list_by_project(project.id)
    goals = [s.goal for s in sessions]
    assert "Session A" in goals
    assert "Session B" in goals


def test_session_checkpoint_resumability(project):
    """Verify startup context can surface last checkpoint summary."""
    s = Session.create(project_id=project.id, goal="Implement auth")
    s.close(summary="JWT added", next_steps="Add refresh token logic")
    last = Session.get_latest_closed(project.id)
    assert last.summary == "JWT added"
    assert last.next_steps == "Add refresh token logic"
