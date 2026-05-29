"""Workflow service for orchestrating task starts and finishes."""

from __future__ import annotations

import subprocess
from typing import Any

from engram.context.startup import (
    build_startup_context,
)
from engram.memory_retrieval import orchestrate_startup_task_memory_retrieval
from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task, get_effective_phase_title
from engram.services.errors import EngramServiceError
from engram.services.serializers import task_to_dict
from engram.services.workflow_helpers import (
    get_target_branch,
    is_same_phase,
    resolve_commit_type,
    select_task_to_start,
    slugify,
)

CONVENTIONAL_COMMIT_TYPES: set[str] = {
    "feat",
    "fix",
    "docs",
    "chore",
    "refactor",
    "test",
    "ci",
    "style",
    "perf",
}


def _run(args: list[str], cwd: str) -> str:
    res = subprocess.run(args, capture_output=True, text=True, cwd=cwd, stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        raise EngramServiceError(
            code="GIT_OPERATION_FAILED",
            message=f"Git command {' '.join(args[:2])} failed: {res.stderr.strip() or res.stdout.strip()}",
        )
    return res.stdout.strip()


def start_workflow(project_id: str, repo_path: str) -> dict[str, Any]:
    """Start or resume the next actionable task in the project."""
    project = Project.get(project_id)
    if not project:
        raise EngramServiceError(
            code="PROJECT_NOT_FOUND",
            message=f"Project with ID '{project_id}' not found.",
        )

    phases = Phase.list_by_project(project_id)
    active_phase = next((p for p in phases if p.status == "active"), None)
    task, is_resuming = select_task_to_start(project_id)

    if not task:
        startup_res = orchestrate_startup_task_memory_retrieval(
            project=project, active_phase=active_phase, selected_task=None
        )
        context_str = build_startup_context(
            project=project,
            active_phase=active_phase,
            selected_task=None,
            startup_task_memory_result=startup_res,
            branch=None,
            is_resuming=False,
        )
        return {"task": None, "branch": None, "is_resuming": False, "context": context_str}

    target_branch = get_target_branch(task)
    current_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_path)
    is_dirty = bool(_run(["git", "status", "--porcelain"], repo_path))

    if current_branch != target_branch and is_dirty:
        raise EngramServiceError(
            code="DIRTY_WORKING_TREE",
            message=f"Git working tree is dirty, and starting this task requires branch '{target_branch}'.",
        )

    if not is_resuming:
        task.update(status="in-progress")

    show = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{target_branch}"],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        cwd=repo_path,
    )
    cmd = (
        ["git", "checkout", target_branch]
        if show.returncode == 0
        else ["git", "checkout", "-b", target_branch]
    )
    _run(cmd, repo_path)

    startup_res = orchestrate_startup_task_memory_retrieval(
        project=project, active_phase=active_phase, selected_task=task
    )
    context_str = build_startup_context(
        project=project,
        active_phase=active_phase,
        selected_task=task,
        startup_task_memory_result=startup_res,
        branch=target_branch,
        is_resuming=is_resuming,
    )

    return {
        "task": task_to_dict(task),
        "branch": target_branch,
        "is_resuming": is_resuming,
        "context": context_str,
    }


def finish_workflow(
    project_id: str, repo_path: str, commit_type: str | None = None
) -> dict[str, Any]:
    """Finish the active task: commit, push, and mark done."""
    project = Project.get(project_id)
    if not project:
        raise EngramServiceError(
            code="PROJECT_NOT_FOUND",
            message=f"Project with ID '{project_id}' not found.",
        )

    tasks = Task.list_by_project(project_id)
    in_progress = [t for t in tasks if t.status == "in-progress"]
    if not in_progress:
        raise EngramServiceError(
            code="NO_TASK_IN_PROGRESS",
            message="No task is currently in-progress.",
        )

    task = in_progress[0]
    try:
        resolved = resolve_commit_type(task, commit_type, CONVENTIONAL_COMMIT_TYPES)
    except ValueError as e:
        raise EngramServiceError(
            code="VALIDATION_ERROR",
            message=f"Invalid commit type '{commit_type}'. Must be one of: {', '.join(sorted(CONVENTIONAL_COMMIT_TYPES))}",
        ) from e

    _run(["git", "add", "-A"], repo_path)

    phase_title = get_effective_phase_title(task)
    commit_msg = f"{resolved}({slugify(phase_title) or 'misc'}): {task.title} [{task.id}]"

    commit_res = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        capture_output=True,
        text=True,
        cwd=repo_path,
        stdin=subprocess.DEVNULL,
    )
    if commit_res.returncode != 0:
        out = (commit_res.stdout + commit_res.stderr).lower()
        if "nothing to commit" not in out:
            raise EngramServiceError(
                code="GIT_OPERATION_FAILED",
                message=f"Git commit failed: {commit_res.stderr.strip() or commit_res.stdout.strip()}",
            )

    _run(["git", "push", "-u", "origin", "HEAD"], repo_path)
    task.update(status="done")

    next_task = Task.get_next(project_id)
    phase_complete = False
    if not next_task or not is_same_phase(next_task, task):
        phase_tasks = [pt for pt in tasks if is_same_phase(pt, task)]
        if all(pt.status in ("done", "cancelled") for pt in phase_tasks):
            phase_complete = True

    return {
        "id": task.id,
        "commit": commit_msg,
        "phase_complete": phase_complete,
    }
