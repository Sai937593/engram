"""Shared pytest fixtures for engram tests."""

import pytest

from engram.db import get_db_connection, init_db


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Provide a fresh temporary SQLite DB for each test.

    Patches the DEFAULT_DB_PATH so every model call uses this isolated DB
    instead of the real ~/.engram/memory.db.
    """
    db_path = tmp_path / "test_memory.db"
    active_project_path = tmp_path / "active_project"
    monkeypatch.setattr("engram.db.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr(
        "engram.services.project_service.ACTIVE_PROJECT_FILE_PATH", active_project_path
    )
    monkeypatch.setattr(
        "engram.models.project.get_db_connection", lambda: get_db_connection(db_path)
    )
    monkeypatch.setattr("engram.models.task.get_db_connection", lambda: get_db_connection(db_path))
    monkeypatch.setattr("engram.models.phase.get_db_connection", lambda: get_db_connection(db_path))
    monkeypatch.setattr(
        "engram.models.memory.get_db_connection", lambda: get_db_connection(db_path)
    )
    monkeypatch.setattr("engram.models.audit.get_db_connection", lambda: get_db_connection(db_path))
    init_db(db_path)
    return db_path


@pytest.fixture
def project(tmp_db):
    """A ready-made project bound to a temp repo path."""
    from engram.models.project import Project

    p = Project.create(
        "test-proj", "Test Project", summary="A test project", repo_paths=["/tmp/test"]
    )
    return p


@pytest.fixture
def task(project):
    """A ready-made todo task."""
    from engram.models.task import Task

    return Task.create(project_id=project.id, title="Do something", priority="high")


@pytest.fixture
def memory(project):
    """A ready-made memory."""
    from engram.models.memory import Memory

    return Memory.create(
        project_id=project.id,
        type="decision",
        title="Use SQLite",
        content="SQLite is good enough for local-first tools.",
        tags=["storage"],
        level="L2",
    )


@pytest.fixture
def mock_startup_context(monkeypatch):
    """Fixture to bypass startup context builder and memory retrieval."""
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        "engram.services.workflow_service.orchestrate_startup_task_memory_retrieval",
        lambda **kwargs: MagicMock(),
    )
    monkeypatch.setattr(
        "engram.services.workflow_service.build_startup_context",
        lambda **kwargs: "mock startup context string",
    )


@pytest.fixture(autouse=True)
def auto_mock_active_project_for_legacy_tests(request, monkeypatch):
    """Automatically mock resolve_active_project to fallback to current project for legacy MCP tests."""
    filename = request.node.fspath.basename
    if filename in ("test_services_project_active.py", "test_mcp_project_tools.py"):
        # Don't mock for our active project specific test files
        return

    try:
        from engram.services.project_service import resolve_current_project

        monkeypatch.setattr(
            "engram.services.project_service.resolve_active_project", resolve_current_project
        )
        monkeypatch.setattr("engram.mcp.tools.resolve_active_project", resolve_current_project)

        from engram.services.context_service import (
            get_handoff_context_for_current_project,
            get_snapshot_context_for_current_project,
            get_startup_context_for_current_project,
            get_task_context_for_current_project,
        )

        monkeypatch.setattr(
            "engram.services.context_service.get_startup_context_for_active_project",
            get_startup_context_for_current_project,
        )
        monkeypatch.setattr(
            "engram.services.context_service.get_task_context_for_active_project",
            get_task_context_for_current_project,
        )
        monkeypatch.setattr(
            "engram.services.context_service.get_snapshot_context_for_active_project",
            get_snapshot_context_for_current_project,
        )
        monkeypatch.setattr(
            "engram.services.context_service.get_handoff_context_for_active_project",
            get_handoff_context_for_current_project,
        )

        monkeypatch.setattr(
            "engram.mcp.resources.get_startup_context_for_active_project",
            get_startup_context_for_current_project,
        )
        monkeypatch.setattr(
            "engram.mcp.resources.get_task_context_for_active_project",
            get_task_context_for_current_project,
        )
        monkeypatch.setattr(
            "engram.mcp.resources.get_snapshot_context_for_active_project",
            get_snapshot_context_for_current_project,
        )
        monkeypatch.setattr(
            "engram.mcp.resources.get_handoff_context_for_active_project",
            get_handoff_context_for_current_project,
        )
    except Exception:
        pass
