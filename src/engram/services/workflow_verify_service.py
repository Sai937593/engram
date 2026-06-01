"""Workflow verification execution service."""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any

from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError
from engram.services.workflow_verification_service import record_workflow_verification

VERIFY_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("ruff", "format", "."),
    ("ruff", "check", ".", "--fix"),
    ("engram.hooks.py_structure",),
    ("pytest", "tests/", "-m", "not slow", "-x", "--tb=short", "-q"),
)


def _extract_actionable_target(output: str) -> str | None:
    for line in output.splitlines():
        match = re.search(r"^([^:\s]+\.(?:py|pyi):\d+:\d+):\s", line.strip())
        if match:
            return match.group(1)
    for line in output.splitlines():
        match = re.search(r"^FAILED\s+([^\s]+)", line.strip())
        if match:
            return match.group(1)
    for line in output.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:140]
    return None


def _compact_failure_details(command: str, exit_code: int, output: str) -> str:
    non_empty = [line.strip() for line in output.splitlines() if line.strip()]
    tail = non_empty[-8:]
    preview = "\n".join(tail) if tail else "No output captured."
    return f"Command: `{command}`\nExit code: {exit_code}\n\nOutput tail:\n{preview}"


def _resolve_verify_commands(repo_path: str) -> list[list[str]]:
    if os.path.exists(os.path.join(repo_path, "uv.lock")):
        resolved: list[list[str]] = []
        for cmd in VERIFY_COMMANDS:
            if cmd == ("engram.hooks.py_structure",):
                resolved.append(["uv", "run", "python", "-m", *cmd])
            else:
                resolved.append(["uv", "run", *cmd])
        return resolved
    return [["python", "-m", *cmd] for cmd in VERIFY_COMMANDS]


def verify_workflow(project_id: str, repo_path: str) -> dict[str, Any]:
    """Run local quality checks and persist the verification outcome."""
    project = Project.get(project_id)
    if not project:
        raise EngramServiceError(
            code="PROJECT_NOT_FOUND",
            message=f"Project with ID '{project_id}' not found.",
        )

    tasks = Task.list_by_project(project_id)
    in_progress = [t for t in tasks if t.status in {"in_progress", "in-progress"}]
    if not in_progress:
        raise EngramServiceError(
            code="NO_TASK_IN_PROGRESS",
            message="No task is currently in-progress.",
        )
    task = in_progress[0]

    for cmd in _resolve_verify_commands(repo_path):
        proc = subprocess.run(
            cmd, capture_output=True, text=True, cwd=repo_path, stdin=subprocess.DEVNULL
        )
        output = (proc.stdout or "").strip()
        if proc.stderr:
            output = f"{output}\n{proc.stderr.strip()}".strip()

        if proc.returncode != 0:
            command = " ".join(cmd)
            target = _extract_actionable_target(output)
            summary = (
                f"`{command}` failed. First actionable target: `{target}`."
                if target
                else f"`{command}` failed."
            )
            details = _compact_failure_details(command, proc.returncode, output)
            record = record_workflow_verification(
                project_id=project_id,
                task_id=task.id,
                passed=False,
                summary=summary,
                details=details,
            )
            return {
                "task_id": task.id,
                "task_title": task.title,
                "passed": False,
                "summary": summary,
                "details": details,
                "actionable_target": target,
                "record": record,
            }

    summary = "All local quality checks passed."
    details = (
        "Checks: `uv run ruff format .`, `uv run ruff check . --fix`, "
        '`uv run python -m engram.hooks.py_structure`, `uv run pytest tests/ -m "not slow" -x --tb=short -q`.'
    )
    record = record_workflow_verification(
        project_id=project_id,
        task_id=task.id,
        passed=True,
        summary=summary,
        details=details,
    )
    return {
        "task_id": task.id,
        "task_title": task.title,
        "passed": True,
        "summary": summary,
        "details": details,
        "actionable_target": None,
        "record": record,
    }
