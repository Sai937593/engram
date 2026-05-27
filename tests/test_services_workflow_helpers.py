"""Shared helper mocks and fixtures for workflow service tests."""

from __future__ import annotations

from typing import Any


class MockCompletedProcess:
    """Mock representing the output of a subprocess.run call."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        """Initialize mock process output."""
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class GitMock:
    """Mock implementation of git commands executed via subprocess."""

    def __init__(self) -> None:
        """Initialize git command mocks with default parameters."""
        self.calls: list[list[str]] = []
        self.commits: list[list[str]] = []
        self.branch: str = "main"
        self.status: str = ""
        self.show_ref_returncode: int = 0
        self.add_returncode: int = 0
        self.commit_returncode: int = 0
        self.commit_stdout: str = "[somebranch 12345] commit ok"
        self.commit_stderr: str = ""
        self.push_returncode: int = 0
        self.push_stderr: str = ""

    def __call__(self, args: list[str], **kwargs: Any) -> MockCompletedProcess:
        """Intercept and log subprocess.run git calls."""
        self.calls.append(args)
        if args == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return MockCompletedProcess(0, stdout=self.branch)
        if args == ["git", "status", "--porcelain"]:
            return MockCompletedProcess(0, stdout=self.status)
        if len(args) >= 3 and args[1] == "show-ref" and args[2] == "--verify":
            return MockCompletedProcess(self.show_ref_returncode)
        if len(args) >= 2 and args[1] == "add":
            return MockCompletedProcess(self.add_returncode)
        if len(args) >= 2 and args[1] == "commit":
            self.commits.append(args)
            return MockCompletedProcess(
                self.commit_returncode, stdout=self.commit_stdout, stderr=self.commit_stderr
            )
        if len(args) >= 2 and args[1] == "push":
            return MockCompletedProcess(self.push_returncode, stderr=self.push_stderr)
        return MockCompletedProcess(0)
