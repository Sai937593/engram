"""Tests for plan MCP tools."""

from __future__ import annotations

import os
from typing import Any

import yaml

from engram.models.plan import Plan
from engram.models.project import Project


class MockServer:
    """Mock FastMCP server for registration and handler testing."""

    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, **kwargs: Any) -> Any:
        """Mock the tool decorator."""

        def decorator(func: Any) -> Any:
            self.tools[func.__name__] = func
            return func

        return decorator


def test_register_plan_tools_registers_six_tools() -> None:
    """Verify that register_tools registers all six plan-scoped tools."""
    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    assert "engram_plan_current" in server.tools
    assert "engram_plan_create" in server.tools
    assert "engram_plan_activate" in server.tools
    assert "engram_plan_update" in server.tools
    assert "engram_plan_list" in server.tools
    assert "engram_plan_get" in server.tools


def test_mcp_plan_current_error_when_missing(tmp_db, monkeypatch) -> None:
    """Verify engram_plan_current returns ACTIVE_PLAN_MISSING when no plan is active."""
    cwd = os.path.abspath(".")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    Project.create(
        id="proj-plans-test",
        name="Plans Test Project",
        summary="A test project for plans",
        repo_paths=[cwd],
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_plan_current"]

    res = yaml.safe_load(handler())
    assert res["ok"] is False
    assert res["error"] == "ACTIVE_PLAN_MISSING"
    assert "Create and activate a plan" in res["fix"]


def test_mcp_plan_current_success(tmp_db, monkeypatch) -> None:
    """Verify engram_plan_current returns the active plan when one exists."""
    cwd = os.path.abspath(".")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-plans-test",
        name="Plans Test Project",
        summary="A test project for plans",
        repo_paths=[cwd],
    )

    plan = Plan.create(
        project_id=project.id,
        title="Active Implementation Plan",
        status="active",
        key="p0004",
    )
    project.update(active_plan_id=plan.id)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_plan_current"]

    res = yaml.safe_load(handler())
    assert res["ok"] is True
    assert res["plan"]["id"] == plan.id
    assert res["plan"]["title"] == "Active Implementation Plan"
    assert res["plan"]["status"] == "active"
    assert res["plan"]["key"] == "p0004"


def test_mcp_plan_create_no_activation(tmp_db, monkeypatch) -> None:
    """Verify engram_plan_create creates a plan in draft status by default."""
    cwd = os.path.abspath(".")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-plans-test",
        name="Plans Test Project",
        summary="A test project for plans",
        repo_paths=[cwd],
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_plan_create"]

    res = yaml.safe_load(handler(title="New Plan Title", key="p0005"))
    assert res["ok"] is True
    assert res["plan"]["id"] is not None
    assert res["plan"]["title"] == "New Plan Title"
    assert res["plan"]["status"] == "draft"
    assert res["plan"]["key"] == "p0005"

    # Project pointer should not be updated
    proj = Project.get(project.id)
    assert proj is not None
    assert proj.active_plan_id is None


def test_mcp_plan_create_with_activation(tmp_db, monkeypatch) -> None:
    """Verify engram_plan_create activates the plan when requested."""
    cwd = os.path.abspath(".")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-plans-test",
        name="Plans Test Project",
        summary="A test project for plans",
        repo_paths=[cwd],
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_plan_create"]

    res = yaml.safe_load(handler(title="Immediate Plan", key="p0006", activate=True))
    assert res["ok"] is True
    assert res["plan"]["status"] == "active"

    # Project pointer should be updated
    proj = Project.get(project.id)
    assert proj is not None
    assert proj.active_plan_id == res["plan"]["id"]


def test_mcp_plan_create_duplicate_key(tmp_db, monkeypatch) -> None:
    """Verify engram_plan_create rejects duplicate plan keys in a project."""
    cwd = os.path.abspath(".")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-plans-test",
        name="Plans Test Project",
        summary="A test project for plans",
        repo_paths=[cwd],
    )
    Plan.create(
        project_id=project.id,
        title="Existing Plan",
        key="p0004",
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_plan_create"]

    res = yaml.safe_load(handler(title="Second Plan", key="p0004"))
    assert res["ok"] is False
    assert res["error"] == "DUPLICATE_PLAN_KEY"
    assert "Choose a different plan key" in res["fix"]


def test_mcp_plan_activate_and_mutual_exclusion(tmp_db, monkeypatch) -> None:
    """Verify engram_plan_activate sets target plan active and deactivates others."""
    cwd = os.path.abspath(".")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-plans-test",
        name="Plans Test Project",
        summary="A test project for plans",
        repo_paths=[cwd],
    )
    plan1 = Plan.create(
        project_id=project.id,
        title="Plan 1",
        key="p0001",
        status="active",
    )
    project.update(active_plan_id=plan1.id)

    plan2 = Plan.create(
        project_id=project.id,
        title="Plan 2",
        key="p0002",
        status="draft",
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_plan_activate"]

    # Activate Plan 2 by its key
    res = yaml.safe_load(handler(plan_ref="p0002"))
    assert res["ok"] is True
    assert res["plan"]["id"] == plan2.id
    assert res["plan"]["status"] == "active"

    # Check Plan 1 is now 'draft' (deactivated)
    p1 = Plan.get(plan1.id)
    assert p1 is not None
    assert p1.status == "draft"

    # Project pointer should point to plan 2
    proj = Project.get(project.id)
    assert proj is not None
    assert proj.active_plan_id == plan2.id

    # Activate non-existent plan
    res_err = yaml.safe_load(handler(plan_ref="p9999"))
    assert res_err["ok"] is False
    assert res_err["error"] == "PLAN_NOT_FOUND"


def test_mcp_plan_update_metadata_and_status(tmp_db, monkeypatch) -> None:
    """Verify engram_plan_update updates metadata, deactivates others if active, clears project active_plan_id if demoted."""
    cwd = os.path.abspath(".")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-plans-test",
        name="Plans Test Project",
        summary="A test project for plans",
        repo_paths=[cwd],
    )
    plan = Plan.create(
        project_id=project.id,
        title="Original Title",
        key="p0004",
        status="active",
        source_doc_path="docs/plans/p0004/adr.md",
    )
    project.update(active_plan_id=plan.id)

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_plan_update"]

    # 1. Update title and slug
    res = yaml.safe_load(handler(plan_ref="p0004", title="New Plan Title", slug="new-plan-slug"))
    assert res["ok"] is True
    assert res["plan"]["title"] == "New Plan Title"
    assert res["plan"]["slug"] == "new-plan-slug"
    assert res["plan"]["status"] == "active"
    assert res["plan"]["source_doc_path"] == "docs/plans/p0004/adr.md"

    # 2. Update status to 'done' (clears project active_plan_id pointer)
    res_done = yaml.safe_load(handler(plan_ref="p0004", status="done"))
    assert res_done["ok"] is True
    assert res_done["plan"]["status"] == "done"

    proj = Project.get(project.id)
    assert proj is not None
    assert proj.active_plan_id is None

    # 3. Update status back to 'active' (verifies activation deactivates others and restores project pointer)
    plan2 = Plan.create(
        project_id=project.id,
        title="Other Plan",
        key="p0005",
        status="active",
    )
    project.update(active_plan_id=plan2.id)

    res_active = yaml.safe_load(handler(plan_ref="p0004", status="active"))
    assert res_active["ok"] is True
    assert res_active["plan"]["status"] == "active"

    # Plan 2 is deactivated
    p2 = Plan.get(plan2.id)
    assert p2 is not None
    assert p2.status == "draft"

    # Project pointer restored to plan 1
    proj = Project.get(project.id)
    assert proj is not None
    assert proj.active_plan_id == plan.id


def test_mcp_plan_list_and_filters(tmp_db, monkeypatch) -> None:
    """Verify engram_plan_list filters by status properly."""
    cwd = os.path.abspath(".")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-plans-test",
        name="Plans Test Project",
        repo_paths=[cwd],
    )
    Plan.create(project_id=project.id, title="P1", key="p0001", status="active")
    Plan.create(project_id=project.id, title="P2", key="p0002", status="draft")
    Plan.create(project_id=project.id, title="P3", key="p0003", status="done")

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_plan_list"]

    # List all
    res_all = yaml.safe_load(handler())
    assert res_all["ok"] is True
    assert res_all["count"] == 3
    assert res_all["filters"]["status"] == "all"
    assert {p["key"] for p in res_all["items"]} == {"p0001", "p0002", "p0003"}

    # Filter active
    res_active = yaml.safe_load(handler(status="active"))
    assert res_active["ok"] is True
    assert res_active["count"] == 1
    assert res_active["items"][0]["key"] == "p0001"

    # Filter invalid status
    res_err = yaml.safe_load(handler(status="invalid_status"))
    assert res_err["ok"] is False
    assert res_err["error"] == "INVALID_PLAN_STATUS"


def test_mcp_plan_get(tmp_db, monkeypatch) -> None:
    """Verify engram_plan_get returns details of a plan."""
    cwd = os.path.abspath(".")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-plans-test",
        name="Plans Test Project",
        repo_paths=[cwd],
    )
    plan = Plan.create(
        project_id=project.id,
        title="Plan Key p0004",
        key="p0004",
        status="draft",
    )

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    handler = server.tools["engram_plan_get"]

    # Get by ID
    res1 = yaml.safe_load(handler(plan_ref=plan.id))
    assert res1["ok"] is True
    assert res1["plan"]["key"] == "p0004"
    assert res1["plan"]["title"] == "Plan Key p0004"

    # Get by Key
    res2 = yaml.safe_load(handler(plan_ref="p0004"))
    assert res2["ok"] is True
    assert res2["plan"]["id"] == plan.id

    # Get non-existent
    res_err = yaml.safe_load(handler(plan_ref="nonexistent"))
    assert res_err["ok"] is False
    assert res_err["error"] == "PLAN_NOT_FOUND"
