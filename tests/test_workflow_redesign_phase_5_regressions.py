"""Regression tests for Phase 5 Markdown-first workflow output contracts."""

from __future__ import annotations

import asyncio
import os
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError
from engram.services.workflow_formatter import (
    format_finish_blocked,
    format_finish_success,
    format_start_blocked,
    format_work_order,
)
from engram.services.workflow_service import finish_workflow, start_workflow
from tests.test_mcp_tools import MockServer
from tests.test_services_workflow_helpers import GitMock


def test_format_functions_have_exactly_one_next_action() -> None:
    """Assert that the primary format helpers each produce exactly one 'Next action' section."""
    # 1. format_work_order
    wo = format_work_order(
        status="starting",
        task_id="t-1",
        task_title="Test Task",
        phase_title="Phase One",
        phase_id="ph-1",
        branch="feat/test",
        objective="Do the thing",
        acceptance="All green",
        task_context=["Task: Test Task (t-1)", "Phase: Phase One (ph-1)"],
        relevant_files=["file1.py"],
        start_hints=None,
        guardrails=["No print statements"],
        memories=["Memory snippet"],
        next_action="Go execute",
    )
    assert wo.count("## Next action") == 1
    assert wo.startswith("# Work Order")

    # 2. format_start_blocked
    sb = format_start_blocked(reason="Dirty tree", next_guidance="Stash first")
    assert sb.count("## Next action") == 1
    assert sb.startswith("# Start Blocked")

    # 3. format_finish_blocked
    fb = format_finish_blocked(
        task_id="t-1", reason="Dirty tree", next_guidance="Stash first", task_title="Test Task"
    )
    assert fb.count("## Next action") == 1
    assert fb.startswith("# Finish Blocked")

    # 4. format_finish_success
    fs = format_finish_success(
        task_id="t-1",
        commit_msg="feat: commit",
        phase_complete=False,
        next_guidance="Stop here",
        task_title="Test Task",
    )
    assert fs.count("## Next action") == 1
    assert fs.startswith("# Task Finished")


def test_successful_start_contract(tmp_db: Any, monkeypatch: Any) -> None:
    """Verify successful workflow start returns compact Markdown Work Order with singular Next action and no YAML dumps."""
    cwd = os.path.abspath("repo/bound-mcp-workflow-start")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-start-ok",
        name="Workflow Start Project",
        summary="Service testing start workflow",
        repo_paths=[cwd],
    )
    Phase.create(project_id=project.id, id="ph-1", title="Phase One", status="active")
    Task.create(
        project_id=project.id,
        id="t-1",
        title="Fix startup bugs",
        phase="Phase One",
        phase_id="ph-1",
        status="todo",
        description="Fix the bugs in start logic",
        acceptance="It works",
        relevant_files=["src/start.py"],
    )

    git_mock = GitMock()
    git_mock.branch = "main"
    git_mock.status = ""
    git_mock.show_ref_returncode = 0

    # 2. Test MCP tool layer output contract setup
    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    start_handler = server.tools["engram_workflow_start"]

    # 1. Test Service layer and 2. Test MCP tool layer output contract
    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = start_workflow("proj-start-ok", cwd)
        res_mcp = asyncio.run(start_handler())

    assert res["task"]["id"] == "t-1"
    assert res["branch"] == "feat/phase-phase-one"
    assert res["is_resuming"] is False

    context = res["context"]
    assert context.startswith("# Work Order")
    assert "Branch: `feat/phase-phase-one`" in context
    assert "## Objective" in context
    assert "Fix the bugs in start logic" in context
    assert "## Acceptance" in context
    assert "It works" in context
    assert "## Start here" in context
    assert "- src/start.py" in context
    assert "## Next action" in context
    assert "Before coding: run engram_memory_search" in context

    # Check non-duplication
    assert context.count("## Next action") == 1
    assert "status:" not in context.lower()
    assert "task_id:" not in context.lower()

    # engram_workflow_start should return the context string directly
    assert res_mcp.startswith("# Work Order")
    assert res_mcp.count("## Next action") == 1
    assert "status:" not in res_mcp.lower()


def test_blocked_start_contract(tmp_db: Any, monkeypatch: Any) -> None:
    """Verify that a blocked start checks tree safety and returns correct error or formatted blocked response."""
    cwd = os.path.abspath("repo/bound-mcp-workflow-start-blocked")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-start-blocked",
        name="Workflow Start Blocked Project",
        summary="Service testing start workflow blocked",
        repo_paths=[cwd],
    )
    Phase.create(project_id=project.id, id="ph-1", title="Phase One", status="active")
    Task.create(
        project_id=project.id,
        id="t-1",
        title="Fix startup bugs",
        phase="Phase One",
        phase_id="ph-1",
        status="todo",
    )

    git_mock = GitMock()
    git_mock.branch = "main"
    git_mock.status = " M modified_file.py"  # Dirty tree

    # 1. Service layer raises DIRTY_WORKING_TREE
    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        with pytest.raises(EngramServiceError) as exc_info:
            start_workflow("proj-start-blocked", cwd)

    assert exc_info.value.code == "DIRTY_WORKING_TREE"
    assert "working tree is dirty" in exc_info.value.message

    # 2. MCP layer returns a flat YAML error response with a fix field
    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)

    start_handler = server.tools["engram_workflow_start"]
    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res_mcp = yaml.safe_load(asyncio.run(start_handler()))

    assert res_mcp["ok"] is False
    assert res_mcp["error"] == "DIRTY_WORKING_TREE"
    assert "fix" in res_mcp
    assert "engram_" in res_mcp["fix"]


def test_start_contract_sparse_metadata_in_service_and_mcp(tmp_db: Any, monkeypatch: Any) -> None:
    """Verify sparse startup still returns compact actionable Work Order in both service and MCP paths."""
    cwd = os.path.abspath("repo/bound-mcp-workflow-start-sparse")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-start-sparse",
        name="Workflow Start Sparse Project",
        summary="Sparse startup contract validation",
        repo_paths=[cwd],
    )
    Phase.create(project_id=project.id, id="ph-sparse", title="Phase Sparse", status="active")
    Task.create(
        project_id=project.id,
        id="t-sparse",
        title="Sparse task title",
        phase="Phase Sparse",
        phase_id="ph-sparse",
        status="todo",
        tags=["sparse", "startup", "guidance"],
    )

    git_mock = GitMock()
    git_mock.branch = "main"
    git_mock.status = ""
    git_mock.show_ref_returncode = 0

    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    start_handler = server.tools["engram_workflow_start"]

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res = start_workflow("proj-start-sparse", cwd)
        res_mcp = asyncio.run(start_handler())

    context = res["context"]
    assert context.startswith("# Work Order")
    assert context.count("## Next action") == 1
    assert "## Start here" in context
    assert "Search the codebase using engram_memory_search" in context
    assert "- Search hint: Sparse task title" in context
    assert "- Search hint: Phase Sparse" in context
    assert "task_id:" not in context.lower()
    assert "status:" not in context.lower()

    assert res_mcp.startswith("# Work Order")
    assert res_mcp.count("## Next action") == 1
    assert "- Search hint: Sparse task title" in res_mcp
    assert "task_id:" not in res_mcp.lower()
    assert "status:" not in res_mcp.lower()


def test_successful_finish_contract(tmp_db: Any, monkeypatch: Any) -> None:
    """Verify successful finish contract for both stop-after-finish (phase not complete) and phase complete states."""
    cwd = os.path.abspath("repo/bound-mcp-workflow-finish")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-finish-ok",
        name="Workflow Finish Project",
        summary="Service testing finish workflow",
        repo_paths=[cwd],
    )
    Phase.create(project_id=project.id, id="ph-1", title="Phase One", status="active")

    # We will create two tasks to test both cases:
    # t-1 (finished while t-2 is still todo -> phase not complete)
    # t-2 (finished when no other tasks remain -> phase complete)
    Task.create(
        project_id=project.id,
        id="t-1",
        title="Refactor auth",
        phase="Phase One",
        phase_id="ph-1",
        status="in-progress",
    )
    Task.create(
        project_id=project.id,
        id="t-2",
        title="Write tests",
        phase="Phase One",
        phase_id="ph-1",
        status="todo",
    )

    git_mock = GitMock()
    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    finish_handler = server.tools["engram_workflow_finish"]

    # --- Case A: Phase Not Complete (Stop-after-finish contract) ---
    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res_mcp_a = asyncio.run(finish_handler(commit_type="feat"))

    assert res_mcp_a.startswith("# Task Finished")
    assert "Task: `t-1` — Refactor auth" in res_mcp_a
    assert "Commit: `feat(phase-one): Refactor auth [t-1]`" in res_mcp_a
    assert "Phase complete: False" in res_mcp_a
    assert res_mcp_a.count("## Next action") == 1
    assert (
        "Stop here. The active task is finished and committed. Await further instructions."
        in res_mcp_a
    )

    # Refreshed task t-1 is done
    t1_refreshed = Task.get("t-1")
    assert t1_refreshed is not None
    assert t1_refreshed.status == "done"

    # --- Case B: Phase Complete (Transition phase contract) ---
    # Start t-2
    t2 = Task.get("t-2")
    assert t2 is not None
    t2.update(status="in-progress")

    git_mock.calls.clear()
    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res_mcp_b = asyncio.run(finish_handler(commit_type="test"))

    assert res_mcp_b.startswith("# Task Finished")
    assert "Task: `t-2` — Write tests" in res_mcp_b
    assert "Commit: `test(phase-one): Write tests [t-2]`" in res_mcp_b
    assert "Phase complete: True" in res_mcp_b
    assert res_mcp_b.count("## Next action") == 1
    assert (
        "Phase complete. Ask the user for permission to run the engram-phase-transition skill."
        in res_mcp_b
    )

    t2_refreshed = Task.get("t-2")
    assert t2_refreshed is not None
    assert t2_refreshed.status == "done"


def test_finish_failures_contract(tmp_db: Any, monkeypatch: Any) -> None:
    """Verify finish failures raise correct errors at service layer and get flat YAML responses at MCP layer."""
    cwd = os.path.abspath("repo/bound-mcp-workflow-finish-fail")
    monkeypatch.setattr("os.getcwd", lambda: cwd)

    project = Project.create(
        id="proj-finish-fail",
        name="Workflow Finish Fail Project",
        summary="Service testing finish workflow errors",
        repo_paths=[cwd],
    )

    # 1. No task in-progress (raises NO_TASK_IN_PROGRESS)
    with pytest.raises(EngramServiceError) as exc_info:
        finish_workflow("proj-finish-fail", cwd)

    assert exc_info.value.code == "NO_TASK_IN_PROGRESS"

    # MCP tool converts this to flat YAML error response
    server = MockServer()
    from engram.mcp.tools import register_tools

    register_tools(server)
    finish_handler = server.tools["engram_workflow_finish"]

    res_mcp_no_task = yaml.safe_load(asyncio.run(finish_handler()))
    assert res_mcp_no_task["ok"] is False
    assert res_mcp_no_task["error"] == "NO_TASK_IN_PROGRESS"
    assert "fix" in res_mcp_no_task
    assert "engram_" in res_mcp_no_task["fix"]

    # 2. Push fails (raises GIT_OPERATION_FAILED)
    Task.create(
        project_id=project.id,
        id="t-fail",
        title="Broken push",
        phase="Phase One",
        status="in-progress",
    )

    git_mock = GitMock()
    git_mock.push_returncode = 1
    git_mock.push_stderr = "remote connection closed"

    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        with pytest.raises(EngramServiceError) as exc_info:
            finish_workflow("proj-finish-fail", cwd)

    assert exc_info.value.code == "GIT_OPERATION_FAILED"

    # MCP tool response
    with patch("engram.services.workflow_service.subprocess.run", side_effect=git_mock):
        res_mcp_push_fail = yaml.safe_load(asyncio.run(finish_handler()))

    assert res_mcp_push_fail["ok"] is False
    assert res_mcp_push_fail["error"] == "GIT_OPERATION_FAILED"
