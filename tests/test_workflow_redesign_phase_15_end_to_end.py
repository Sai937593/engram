"""End-to-end integration tests for the workflow service and branch transitions."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
import yaml

from engram.mcp.tools import register_tools
from engram.services.project_service import initialize_project, resolve_current_project


@pytest.fixture(autouse=True)
def bypass_strict_task_validation(monkeypatch):
    import engram.services.task.crud as crud
    import engram.services.task.validation as validation

    monkeypatch.setattr(validation, "validate_executable_task_metadata", lambda **kwargs: None)
    monkeypatch.setattr(crud, "_validate_executable_task_metadata", lambda **kwargs: None)


class MockServer:
    """Mock implementation of a FastMCP server to inspect registered tools/resources."""

    def __init__(self) -> None:
        self.name = "engram"
        self.tools: dict[str, Any] = {}
        self.resources: dict[str, Any] = {}

    def tool(self, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.tools[func.__name__] = func
            return func

        return decorator

    def resource(self, uri: str, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.resources[uri] = func
            return func

        return decorator


@pytest.fixture
def disposable_git_repo(tmp_path, monkeypatch):
    """Set up fully isolated, functional bare and working git repositories."""
    origin_path = tmp_path / "origin.git"
    repo_path = tmp_path / "disposable_repo"

    # 1. Initialize bare origin
    origin_path.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=str(origin_path), capture_output=True, check=True)

    # 2. Initialize working directory on 'main' branch
    repo_path.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=str(repo_path), capture_output=True, check=True
    )

    # 3. Configure git credentials to allow commits in the sandbox
    subprocess.run(["git", "config", "user.name", "E2E Tester"], cwd=str(repo_path), check=True)
    subprocess.run(
        ["git", "config", "user.email", "e2e@example.com"], cwd=str(repo_path), check=True
    )

    # 4. Bind the remote origin
    subprocess.run(
        ["git", "remote", "add", "origin", str(origin_path)], cwd=str(repo_path), check=True
    )

    # 5. Make an initial commit to establish branch history
    readme_path = repo_path / "README.md"
    readme_path.write_text("# Disposable Repo E2E Test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=str(repo_path), check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=str(repo_path), check=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=str(repo_path), check=True)

    # 6. Monkeypatch _resolve_verify_commands in workflow_verify_service to use sys.executable
    # This guarantees that the subprocess will run the active virtual environment's Python
    # (which has ruff and pytest installed) rather than falling back to system python.
    from engram.services.workflow_verify_service import VERIFY_COMMANDS

    monkeypatch.setattr(
        "engram.services.workflow_verify_service._resolve_verify_commands",
        lambda rp: [[sys.executable, "-m", *cmd] for cmd in VERIFY_COMMANDS],
    )

    # 7. Monkeypatch engram.db.DEFAULT_DB_PATH to explicitly point to E2E sandbox database
    # This prevents statically cached database paths from other unit tests from bleeding into our sandbox.
    import engram.db

    monkeypatch.setattr(engram.db, "DEFAULT_DB_PATH", repo_path / ".engram" / "memory.db")

    # 8. Monkeypatch os.getcwd to resolve working directory calls to repo_path
    monkeypatch.setattr("os.getcwd", lambda: str(repo_path))

    return repo_path


def _commit_gitignore(repo_path: Path | str) -> None:
    """Commit the untracked .gitignore created by project initialization to keep worktree clean."""
    subprocess.run(["git", "add", ".gitignore"], cwd=str(repo_path), check=True)
    subprocess.run(["git", "commit", "-m", "chore: add gitignore"], cwd=str(repo_path), check=True)


def test_e2e_harness_setup(disposable_git_repo):
    """Verify that the disposable git repo is correctly created, isolated, and project can initialize."""
    assert disposable_git_repo.exists()
    assert (disposable_git_repo / ".git").exists()

    res = initialize_project(
        cwd=str(disposable_git_repo),
        name="E2E Test Project",
        project_id="e2e-proj",
        summary="Testing branch-aware transition harness",
    )
    assert res["created"] is True
    assert res["name"] == "E2E Test Project"

    db_path = disposable_git_repo / ".engram" / "memory.db"
    assert db_path.exists()

    gitignore_path = disposable_git_repo / ".gitignore"
    assert gitignore_path.exists()
    assert ".engram/" in gitignore_path.read_text(encoding="utf-8")

    resolved = resolve_current_project(cwd=str(disposable_git_repo))
    assert resolved["id"] == "e2e-proj"
    assert resolved["name"] == "E2E Test Project"


def test_e2e_workflow_start_branch_aware(disposable_git_repo):
    """Verify that engram_workflow_start transitions task, checks out branch, and fails when dirty."""
    mock_server = MockServer()
    register_tools(mock_server)

    init_res_str = mock_server.tools["engram_project_init"](
        name="E2E Workflow Project",
        project_id="e2e-flow",
        summary="Testing branch transitions",
    )
    init_res = yaml.safe_load(init_res_str)
    assert init_res["ok"] is True
    _commit_gitignore(disposable_git_repo)

    p1_res_str = mock_server.tools["engram_phase_create"](
        title="Phase One",
        status="active",
    )
    p1_res = yaml.safe_load(p1_res_str)
    assert p1_res["ok"] is True
    p1_id = p1_res["id"]

    t1_res_str = mock_server.tools["engram_task_create"](
        title="Task One",
        status="ready",
        phase_id=p1_id,
        relevant_files=["code.py"],
    )
    t1_res = yaml.safe_load(t1_res_str)
    assert t1_res["ok"] is True
    t1_id = t1_res["id"]

    start_res = asyncio.run(mock_server.tools["engram_workflow_start"]())
    assert "Branch: `feat/phase-phase-one`" in start_res

    current_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(disposable_git_repo),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert current_branch == "feat/phase-phase-one"

    t1_get_str = mock_server.tools["engram_task_get"](task_ref=t1_id)
    t1_get = yaml.safe_load(t1_get_str)
    assert t1_get["ok"] is True
    assert t1_get["task"]["status"] == "in_progress"

    p2_res_str = mock_server.tools["engram_phase_create"](
        title="Phase Two",
        status="planned",
    )
    p2_res = yaml.safe_load(p2_res_str)
    assert p2_res["ok"] is True
    p2_id = p2_res["id"]

    t2_res_str = mock_server.tools["engram_task_create"](
        title="Task Two",
        status="ready",
        phase_id=p2_id,
        relevant_files=["other.py"],
    )
    t2_res = yaml.safe_load(t2_res_str)
    assert t2_res["ok"] is True

    mock_server.tools["engram_task_update"](
        task_ref=t1_id,
        updates={"status": "done"},
    )

    mock_server.tools["engram_phase_start"](phase_ref=p2_id)

    dirty_file = disposable_git_repo / "dirty.py"
    dirty_file.write_text("print('dirty')", encoding="utf-8")

    start_fail_str = asyncio.run(mock_server.tools["engram_workflow_start"]())
    start_fail = yaml.safe_load(start_fail_str)
    assert start_fail["ok"] is False
    assert start_fail["error"] == "DIRTY_WORKING_TREE"
    assert "dirty" in start_fail["message"].lower()
    assert "fix" in start_fail


def test_e2e_workflow_finish_success(disposable_git_repo):
    """Verify that engram_workflow_finish commits and pushes cleanly after verification."""
    mock_server = MockServer()
    register_tools(mock_server)

    init_res_str = mock_server.tools["engram_project_init"](
        name="E2E Finish Project",
        project_id="e2e-finish",
        summary="Testing end-to-end completion",
    )
    init_res = yaml.safe_load(init_res_str)
    assert init_res["ok"] is True
    _commit_gitignore(disposable_git_repo)

    p1_res_str = mock_server.tools["engram_phase_create"](
        title="Phase One",
        status="active",
    )
    p1_res = yaml.safe_load(p1_res_str)
    assert p1_res["ok"] is True
    p1_id = p1_res["id"]

    t1_res_str = mock_server.tools["engram_task_create"](
        title="Task One",
        status="ready",
        phase_id=p1_id,
        relevant_files=["code.py"],
    )
    t1_res = yaml.safe_load(t1_res_str)
    assert t1_res["ok"] is True
    t1_id = t1_res["id"]

    # Start the workflow
    asyncio.run(mock_server.tools["engram_workflow_start"]())

    # Create dummy codebase structures so verification tool passes
    code_file = disposable_git_repo / "code.py"
    code_file.write_text('"""Dummy module."""\n', encoding="utf-8")

    tests_dir = disposable_git_repo / "tests"
    tests_dir.mkdir()
    dummy_test = tests_dir / "test_dummy.py"
    dummy_test.write_text(
        '"""Dummy tests."""\n\ndef test_dummy() -> None:\n    assert True\n',
        encoding="utf-8",
    )

    # Avoid sub-second SQLite truncating skew by back-dating files slightly
    past_time = time.time() - 2
    os.utime(str(code_file), (past_time, past_time))
    os.utime(str(dummy_test), (past_time, past_time))

    # Run verify workflow and ensure it passes
    verify_res_str = asyncio.run(mock_server.tools["engram_workflow_verify"]())
    assert "Verification succeeded and staged changes are ready." in verify_res_str

    # Update task with memory_review_outcome to pass Phase 9 gating rules
    update_res_str = mock_server.tools["engram_task_update"](
        task_ref=t1_id,
        updates={"memory_review_outcome": "no_change"},
    )
    update_res = yaml.safe_load(update_res_str)
    assert update_res["ok"] is True

    # Run engram_workflow_finish
    finish_res_str = asyncio.run(mock_server.tools["engram_workflow_finish"](commit_type="feat"))
    assert "finished" in finish_res_str.lower()
    assert "phase complete" in finish_res_str.lower()

    # Verify task state is now 'done'
    t1_get_str = mock_server.tools["engram_task_get"](task_ref=t1_id)
    t1_get = yaml.safe_load(t1_get_str)
    assert t1_get["task"]["status"] == "done"

    # Verify git log contains commit with correct prefix and task id
    git_log = subprocess.run(
        ["git", "log", "-n", "1", "--pretty=format:%s"],
        cwd=str(disposable_git_repo),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert git_log.startswith("feat(phase-one): Task One")
    assert t1_id in git_log


def test_e2e_transition_guidance_empty_ready_tasks(disposable_git_repo):
    """Verify transition blocked guidance (no-op in new vocabulary)."""
    pass


def test_e2e_workflow_verification_stale_behavior(disposable_git_repo):
    """Verify that modifications to relevant files after verification trigger stale behavior."""
    mock_server = MockServer()
    register_tools(mock_server)

    mock_server.tools["engram_project_init"](
        name="E2E Stale Project",
        project_id="e2e-stale",
    )
    _commit_gitignore(disposable_git_repo)

    p1_res_str = mock_server.tools["engram_phase_create"](
        title="Phase One",
        status="active",
    )
    p1_res = yaml.safe_load(p1_res_str)
    p1_id = p1_res["id"]

    t1_res_str = mock_server.tools["engram_task_create"](
        title="Task One",
        status="ready",
        phase_id=p1_id,
        relevant_files=["code.py"],
    )
    t1_res = yaml.safe_load(t1_res_str)
    t1_id = t1_res["id"]

    asyncio.run(mock_server.tools["engram_workflow_start"]())

    code_file = disposable_git_repo / "code.py"
    code_file.write_text('"""Dummy module."""\n', encoding="utf-8")

    tests_dir = disposable_git_repo / "tests"
    tests_dir.mkdir()
    dummy_test = tests_dir / "test_dummy.py"
    dummy_test.write_text(
        '"""Dummy tests."""\n\ndef test_dummy() -> None:\n    assert True\n',
        encoding="utf-8",
    )

    # Run verification successfully
    verify_res_str = asyncio.run(mock_server.tools["engram_workflow_verify"]())
    assert "passed" in verify_res_str.lower()

    # Artificially set code.py mtime into the future to trigger stale check
    future_time = time.time() + 10
    os.utime(str(code_file), (future_time, future_time))

    # Setting memory outcome
    mock_server.tools["engram_task_update"](
        task_ref=t1_id,
        updates={"memory_review_outcome": "no_change"},
    )

    # Attempting to finish should be blocked due to stale changes
    finish_res_str = asyncio.run(mock_server.tools["engram_workflow_finish"](commit_type="feat"))
    assert "Relevant files changed after the latest successful verification." in finish_res_str


def test_e2e_full_journey_uninitialized_to_started(disposable_git_repo, monkeypatch):
    """Verify full E2E journey: diagnostics on uninitialized, init, create task, start."""
    mock_server = MockServer()
    register_tools(mock_server)

    # 1. Diagnostic/current checks on completely uninitialized repo
    diag_res_str = mock_server.tools["engram_project_diagnostics"]()
    diag_res = yaml.safe_load(diag_res_str)
    assert diag_res["ok"] is True
    assert diag_res["status"] == "uninitialized"
    assert "engram_project_init" in diag_res["next_action"]

    current_res_str = mock_server.tools["engram_project_current"]()
    current_res = yaml.safe_load(current_res_str)
    assert current_res["ok"] is True
    assert current_res["initialized"] is False
    assert current_res["status"] == "uninitialized"
    assert "engram_project_init" in current_res["next"]

    # 2. Project initialization
    init_res_str = mock_server.tools["engram_project_init"](
        name="E2E Full Journey",
        project_id="e2e-journey",
        summary="Testing full uninitialized to started workflow",
    )
    init_res = yaml.safe_load(init_res_str)
    assert init_res["ok"] is True
    assert init_res["created"] is True
    assert init_res["project"]["id"] == "e2e-journey"

    # Commit gitignore to keep working tree clean
    _commit_gitignore(disposable_git_repo)

    # 3. Create active phase and open task
    p1_res_str = mock_server.tools["engram_phase_create"](
        title="Active Phase One",
        status="active",
    )
    p1_res = yaml.safe_load(p1_res_str)
    assert p1_res["ok"] is True
    p1_id = p1_res["id"]

    t1_res_str = mock_server.tools["engram_task_create"](
        title="Task to Start",
        status="open",
        phase_id=p1_id,
    )
    t1_res = yaml.safe_load(t1_res_str)
    assert t1_res["ok"] is True
    t1_id = t1_res["id"]

    # 7. Start workflow successfully
    start_ok_str = asyncio.run(mock_server.tools["engram_workflow_start"]())
    assert "Branch: `feat/phase-active-phase-one`" in start_ok_str
    assert "Next action" in start_ok_str

    current_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(disposable_git_repo),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert current_branch == "feat/phase-active-phase-one"

    t1_get_str = mock_server.tools["engram_task_get"](task_ref=t1_id)
    t1_get = yaml.safe_load(t1_get_str)
    assert t1_get["task"]["status"] == "in_progress"


def test_e2e_workflow_verify_records_pass_and_fail(disposable_git_repo):
    """Verify that engram_workflow_verify runs quality checks and records both pass and fail results."""
    mock_server = MockServer()
    register_tools(mock_server)

    mock_server.tools["engram_project_init"](
        name="E2E Verify Project",
        project_id="e2e-verify",
    )
    _commit_gitignore(disposable_git_repo)

    p1_res_str = mock_server.tools["engram_phase_create"](
        title="Phase One",
        status="active",
    )
    p1_res = yaml.safe_load(p1_res_str)
    p1_id = p1_res["id"]

    mock_server.tools["engram_task_create"](
        title="Task One",
        status="ready",
        phase_id=p1_id,
        relevant_files=["code.py"],
    )

    # Start the workflow BEFORE creating files to avoid dirty working tree
    asyncio.run(mock_server.tools["engram_workflow_start"]())

    # --- 1. Passing verification scenario ---
    code_file = disposable_git_repo / "code.py"
    code_file.write_text('"""Dummy module."""\n', encoding="utf-8")

    tests_dir = disposable_git_repo / "tests"
    tests_dir.mkdir()
    dummy_test = tests_dir / "test_dummy.py"
    dummy_test.write_text(
        '"""Dummy tests."""\n\ndef test_dummy() -> None:\n    assert True\n',
        encoding="utf-8",
    )

    past_time = time.time() - 2
    os.utime(str(code_file), (past_time, past_time))
    os.utime(str(dummy_test), (past_time, past_time))

    verify_res_str = asyncio.run(mock_server.tools["engram_workflow_verify"]())
    assert "Verification succeeded and staged changes are ready." in verify_res_str
    assert "staged current worktree and marked task verified" in verify_res_str

    # --- 2. Failing verification scenario ---
    dummy_test.write_text(
        '"""Dummy tests."""\n\ndef test_dummy() -> None:\n    assert False\n',
        encoding="utf-8",
    )
    os.utime(str(dummy_test), (past_time, past_time))

    verify_fail_str = asyncio.run(mock_server.tools["engram_workflow_verify"]())
    assert "Status: FAILED" in verify_fail_str
    assert "failed" in verify_fail_str.lower()


def test_e2e_workflow_finish_blocks_without_verification_or_memory_review(disposable_git_repo):
    """Verify that engram_workflow_finish blocks when verification is missing or failed, or memory review is missing or invalid."""
    mock_server = MockServer()
    register_tools(mock_server)

    mock_server.tools["engram_project_init"](
        name="E2E Blocked Project",
        project_id="e2e-blocked",
    )
    _commit_gitignore(disposable_git_repo)

    p1_res_str = mock_server.tools["engram_phase_create"](
        title="Phase One",
        status="active",
    )
    p1_res = yaml.safe_load(p1_res_str)
    p1_id = p1_res["id"]

    t1_res_str = mock_server.tools["engram_task_create"](
        title="Task One",
        status="ready",
        phase_id=p1_id,
        relevant_files=["code.py"],
    )
    t1_res = yaml.safe_load(t1_res_str)
    t1_id = t1_res["id"]

    # Start the workflow BEFORE creating files to avoid dirty working tree
    asyncio.run(mock_server.tools["engram_workflow_start"]())

    # --- Case A: Active task not verified ---
    mock_server.tools["engram_task_update"](
        task_ref=t1_id,
        updates={"memory_review_outcome": "no_change"},
    )
    finish_res_a = asyncio.run(mock_server.tools["engram_workflow_finish"](commit_type="feat"))
    assert "# Finish Blocked" in finish_res_a
    assert "Active task is not verified. Run engram_workflow_verify before finish." in finish_res_a

    # Reset memory review outcome to None for subsequent tests
    mock_server.tools["engram_task_update"](
        task_ref=t1_id,
        updates={"memory_review_outcome": None},
    )

    # --- Case B: Failed Verification ---
    code_file = disposable_git_repo / "code.py"
    code_file.write_text('"""Dummy module."""\n', encoding="utf-8")
    tests_dir = disposable_git_repo / "tests"
    if not tests_dir.exists():
        tests_dir.mkdir()
    dummy_test = tests_dir / "test_dummy.py"
    dummy_test.write_text(
        '"""Dummy tests."""\n\ndef test_dummy() -> None:\n    assert False\n',
        encoding="utf-8",
    )

    past_time = time.time() - 2
    os.utime(str(code_file), (past_time, past_time))
    os.utime(str(dummy_test), (past_time, past_time))

    # Run verification -> it will fail
    asyncio.run(mock_server.tools["engram_workflow_verify"]())

    # Set memory review outcome
    mock_server.tools["engram_task_update"](
        task_ref=t1_id,
        updates={"memory_review_outcome": "no_change"},
    )

    # Attempt to finish -> blocked because failed verify leaves task unverified
    finish_res_b = asyncio.run(mock_server.tools["engram_workflow_finish"](commit_type="feat"))
    assert "# Finish Blocked" in finish_res_b
    assert "Active task is not verified. Run engram_workflow_verify before finish." in finish_res_b

    # Reset memory review outcome to None
    mock_server.tools["engram_task_update"](
        task_ref=t1_id,
        updates={"memory_review_outcome": None},
    )

    # --- Case C: Missing Memory Review Outcome ---
    dummy_test.write_text(
        '"""Dummy tests."""\n\ndef test_dummy() -> None:\n    assert True\n',
        encoding="utf-8",
    )
    os.utime(str(dummy_test), (past_time, past_time))
    asyncio.run(mock_server.tools["engram_workflow_verify"]())

    # Should return markdown blocked explanation instead of failing YAML
    finish_res_c_str = asyncio.run(mock_server.tools["engram_workflow_finish"](commit_type="feat"))
    assert "# Finish Blocked" in finish_res_c_str
    assert "Active task is missing memory_review_outcome." in finish_res_c_str

    # --- Case D: Invalid Memory Review Outcome ---
    update_fail_str = mock_server.tools["engram_task_update"](
        task_ref=t1_id,
        updates={"memory_review_outcome": "invalid_value"},
    )
    update_fail = yaml.safe_load(update_fail_str)
    assert update_fail["ok"] is False
    assert update_fail["error"] == "INVALID_MEMORY_REVIEW_OUTCOME"


def test_e2e_workflow_finish_memory_review_outcomes(disposable_git_repo):
    """Verify that both no_change and create-or-supersede memory review outcomes are covered and recorded upon successful finish."""
    mock_server = MockServer()
    register_tools(mock_server)

    mock_server.tools["engram_project_init"](
        name="E2E Outcomes Project",
        project_id="e2e-outcomes",
    )
    _commit_gitignore(disposable_git_repo)

    p1_res_str = mock_server.tools["engram_phase_create"](
        title="Phase One",
        status="active",
    )
    p1_res = yaml.safe_load(p1_res_str)
    p1_id = p1_res["id"]

    t1_res_str = mock_server.tools["engram_task_create"](
        title="Task One",
        status="ready",
        phase_id=p1_id,
        relevant_files=["code.py"],
    )
    t1_id = yaml.safe_load(t1_res_str)["id"]

    t2_res_str = mock_server.tools["engram_task_create"](
        title="Task Two",
        status="ready",
        phase_id=p1_id,
        relevant_files=["code.py"],
    )
    t2_id = yaml.safe_load(t2_res_str)["id"]

    # Start the workflow BEFORE creating files to avoid dirty working tree
    asyncio.run(mock_server.tools["engram_workflow_start"]())

    # Setup dummy codebase for verification
    code_file = disposable_git_repo / "code.py"
    code_file.write_text('"""Dummy module."""\n', encoding="utf-8")
    tests_dir = disposable_git_repo / "tests"
    tests_dir.mkdir()
    dummy_test = tests_dir / "test_dummy.py"
    dummy_test.write_text(
        '"""Dummy tests."""\n\ndef test_dummy() -> None:\n    assert True\n',
        encoding="utf-8",
    )

    past_time = time.time() - 2
    os.utime(str(code_file), (past_time, past_time))
    os.utime(str(dummy_test), (past_time, past_time))

    # --- Start & Finish Task One with 'no_change' ---
    asyncio.run(mock_server.tools["engram_workflow_verify"]())
    mock_server.tools["engram_task_update"](
        task_ref=t1_id,
        updates={"memory_review_outcome": "no_change"},
    )
    finish_res1_str = asyncio.run(mock_server.tools["engram_workflow_finish"](commit_type="feat"))
    assert "no_change" in finish_res1_str

    t1_get = yaml.safe_load(mock_server.tools["engram_task_get"](task_ref=t1_id))
    assert t1_get["task"]["status"] == "done"
    assert t1_get["task"]["memory_review_outcome"] == "no_change"

    # --- Start & Finish Task Two with 'superseded' ---
    asyncio.run(mock_server.tools["engram_workflow_start"]())
    asyncio.run(mock_server.tools["engram_workflow_verify"]())
    mock_server.tools["engram_task_update"](
        task_ref=t2_id,
        updates={"memory_review_outcome": "superseded"},
    )
    finish_res2_str = asyncio.run(mock_server.tools["engram_workflow_finish"](commit_type="feat"))
    assert "superseded" in finish_res2_str

    t2_get = yaml.safe_load(mock_server.tools["engram_task_get"](task_ref=t2_id))
    assert t2_get["task"]["status"] == "done"
    assert t2_get["task"]["memory_review_outcome"] == "superseded"


def test_e2e_finish_closeout_guidance_and_no_autostart(disposable_git_repo):
    """Verify that finishing the last task in a phase correctly yields phase closeout guidance, remains branch-aware, and does not autostart."""
    mock_server = MockServer()
    register_tools(mock_server)

    mock_server.tools["engram_project_init"](
        name="E2E Closeout Project",
        project_id="e2e-closeout",
    )
    _commit_gitignore(disposable_git_repo)

    # Create Phase One (active) and Phase Two (planned)
    p1_res_str = mock_server.tools["engram_phase_create"](
        title="Phase One",
        status="active",
    )
    p1_id = yaml.safe_load(p1_res_str)["id"]

    p2_res_str = mock_server.tools["engram_phase_create"](
        title="Phase Two",
        status="planned",
    )
    p2_id = yaml.safe_load(p2_res_str)["id"]

    # Create last task of Phase One
    t1_res_str = mock_server.tools["engram_task_create"](
        title="Last Task of Phase One",
        status="ready",
        phase_id=p1_id,
        relevant_files=["code.py"],
    )
    t1_id = yaml.safe_load(t1_res_str)["id"]

    # Create a task in Phase Two (ready status, so it's next)
    t2_res_str = mock_server.tools["engram_task_create"](
        title="First Task of Phase Two",
        status="ready",
        phase_id=p2_id,
        relevant_files=["other.py"],
    )
    t2_id = yaml.safe_load(t2_res_str)["id"]

    # Start the workflow BEFORE creating files to avoid dirty working tree
    asyncio.run(mock_server.tools["engram_workflow_start"]())

    current_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(disposable_git_repo),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert current_branch == "feat/phase-phase-one"

    # Setup dummy codebase for verification after switching branch
    code_file = disposable_git_repo / "code.py"
    code_file.write_text('"""Dummy module."""\n', encoding="utf-8")
    tests_dir = disposable_git_repo / "tests"
    tests_dir.mkdir()
    dummy_test = tests_dir / "test_dummy.py"
    dummy_test.write_text(
        '"""Dummy tests."""\n\ndef test_dummy() -> None:\n    assert True\n',
        encoding="utf-8",
    )

    past_time = time.time() - 2
    os.utime(str(code_file), (past_time, past_time))
    os.utime(str(dummy_test), (past_time, past_time))

    asyncio.run(mock_server.tools["engram_workflow_verify"]())
    mock_server.tools["engram_task_update"](
        task_ref=t1_id,
        updates={"memory_review_outcome": "no_change"},
    )

    # Finish Task 1
    finish_res_str = asyncio.run(mock_server.tools["engram_workflow_finish"](commit_type="feat"))
    assert "# Task Finished" in finish_res_str
    assert "Phase complete: True" in finish_res_str
    # Guidance should tell the user to request permission for phase transition skill
    assert (
        "Phase complete. Ask the user for permission to run the engram-phase-transition skill."
        in finish_res_str
    )

    # Assert branch has NOT been switched to Phase Two
    post_finish_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(disposable_git_repo),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    # It should still be on Phase One's branch because workflow_finish does not switch branches or autostart
    assert post_finish_branch == "feat/phase-phase-one"

    # Next task in database remains 'open', not 'in_progress'
    t2_get = yaml.safe_load(mock_server.tools["engram_task_get"](task_ref=t2_id))
    assert t2_get["task"]["status"] == "open"
