"""Shared pytest fixtures for engram tests."""

import pytest

from engram.db import get_db_connection, init_db


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Provide a fresh temporary SQLite DB for each test.

    Patches the DEFAULT_DB_PATH so every model call uses this isolated DB
    instead of the real ~/.engram/memory.db.
    """
    import os

    db_path = tmp_path / "test_memory.db"
    monkeypatch.setattr("engram.db.DEFAULT_DB_PATH", db_path)

    # Comprehensive patching of all get_db_connection endpoints
    patch_modules = [
        "engram.db",
        "engram.models.project",
        "engram.models.task.model",
        "engram.models.task.queries",
        "engram.models.phase",
        "engram.models.memory.model",
        "engram.models.memory.queries",
        "engram.models.memory.helpers",
        "engram.models.audit",
        "engram.services.task.validation",
        "engram.services.memory_service",
        "engram.memory_retrieval.semantic_index_storage",
        "engram.memory_retrieval.fts_retriever.retriever",
    ]
    for module in patch_modules:
        try:
            monkeypatch.setattr(
                f"{module}.get_db_connection", lambda *args, **kwargs: get_db_connection(db_path)
            )
        except AttributeError:
            pass

    # Ensure os.getcwd() returns tmp_path to isolate repository traversal in tests
    monkeypatch.setattr("os.getcwd", lambda: str(tmp_path))

    # Intercept os.path.abspath to make relative test paths resolve to the isolated tmp_path
    original_abspath = os.path.abspath

    def safe_abspath(path):
        if not os.path.isabs(path):
            return original_abspath(os.path.join(str(tmp_path), path))
        return original_abspath(path)

    monkeypatch.setattr("os.path.abspath", safe_abspath)

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
