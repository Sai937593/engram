"""Runtime target state for the local Engram UI."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from engram.models.project import Project

DEFAULT_UI_STATE_PATH = Path.home() / ".engram" / "ui_state.json"


class UiStateError(Exception):
    """Raised when the UI cannot resolve or read its active project."""


@dataclass(frozen=True)
class UiTarget:
    """The project currently selected for the local UI."""

    project_id: str
    project_name: str
    repo_path: str
    version: str
    updated_at: str


def resolve_target_from_cwd(cwd: str | os.PathLike[str] | None = None) -> UiTarget:
    """Resolve the UI target from the current directory or containing Git root."""
    cwd_path = Path(cwd or os.getcwd()).resolve()
    git_root = _git_root(cwd_path)
    lookup_path = git_root or cwd_path
    project, repo_path = _resolve_project_for_path(lookup_path)
    return _new_target(project, repo_path)


def write_target(target: UiTarget, state_path: Path | None = None) -> None:
    """Persist the current local UI target."""
    path = state_path or DEFAULT_UI_STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(target), indent=2), encoding="utf-8")


def read_target(state_path: Path | None = None) -> UiTarget | None:
    """Read the current local UI target if one exists."""
    path = state_path or DEFAULT_UI_STATE_PATH
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return UiTarget(
            project_id=str(payload["project_id"]),
            project_name=str(payload["project_name"]),
            repo_path=str(payload["repo_path"]),
            version=str(payload["version"]),
            updated_at=str(payload["updated_at"]),
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise UiStateError(f"UI state is invalid: {path}") from exc


def require_target(state_path: Path | None = None) -> UiTarget:
    """Read the current UI target or fail with a user-facing error."""
    target = read_target(state_path)
    if target is None:
        raise UiStateError("No active Engram UI project. Run 'engram ui' from a registered repo.")
    return target


def _resolve_project_for_path(path: Path) -> tuple[Project, str]:
    path_norm = _normalise_path(path)
    candidates: list[tuple[int, Project, str, str]] = []

    for project in Project.list_all():
        for repo_path in project.repo_paths:
            repo_norm = _normalise_path(repo_path)
            if path_norm == repo_norm or _is_relative_to(path_norm, repo_norm):
                candidates.append((len(repo_norm), project, repo_path, repo_norm))

    if not candidates:
        raise UiStateError(
            "Current directory is not bound to any Engram project. Run 'engram init' "
            "from this repository before launching the UI."
        )

    best_score = max(score for score, _, _, _ in candidates)
    best = [candidate for candidate in candidates if candidate[0] == best_score]
    project_ids = sorted({project.id for _, project, _, _ in best})
    repo_paths = sorted({repo_norm for _, _, _, repo_norm in best})
    if len(project_ids) > 1:
        raise UiStateError(
            "Current directory matches multiple Engram projects "
            f"({', '.join(project_ids)}) for repo path(s): {', '.join(repo_paths)}. "
            "Fix the duplicate project binding before launching the UI."
        )

    _, project, repo_path, _ = best[0]
    return project, repo_path


def _new_target(project: Project, repo_path: str) -> UiTarget:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    return UiTarget(
        project_id=project.id,
        project_name=project.name,
        repo_path=repo_path,
        version=timestamp,
        updated_at=timestamp,
    )


def _git_root(path: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            capture_output=True,
            check=False,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    root = result.stdout.strip()
    return Path(root).resolve() if root else None


def _normalise_path(path: str | os.PathLike[str]) -> str:
    normalised = os.path.normcase(os.path.abspath(os.fspath(path)))
    return normalised.rstrip("\\/")


def _is_relative_to(path_norm: str, parent_norm: str) -> bool:
    if path_norm == parent_norm:
        return True
    return path_norm.startswith(parent_norm + os.sep)
