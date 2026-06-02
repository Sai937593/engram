"""Helper utilities for workflow behavior, independent of CLI context."""

from __future__ import annotations

import re

from engram.models.phase import Phase
from engram.models.task import Task, get_effective_phase_title


def slugify(text: str) -> str:
    """Return a git-safe slug for branch naming."""
    if not text:
        return "misc"
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def get_target_branch(task: Task) -> str:
    """Return the phase branch name for the provided task."""
    phase_title = get_effective_phase_title(task)
    return f"feat/phase-{slugify(phase_title)}" if phase_title else "feat/misc"


def _normalize_phase_title(title: str | None) -> str:
    """Return a case-insensitive, whitespace-normalized title key."""
    if title is None:
        return ""
    return " ".join(title.split()).casefold()


def task_matches_phase(task: Task, phase: Phase) -> bool:
    """Return whether a task is linked to a phase via first-class or legacy data."""
    if task.phase_id == phase.id:
        return True
    if task.phase_id:
        return False
    return _normalize_phase_title(task.phase) == _normalize_phase_title(phase.title)


def resolve_task_phase(project_id: str, task: Task) -> Phase | None:
    """Resolve the phase linked to a task using first-class or legacy identifiers."""
    if task.phase_id:
        phase = Phase.get(task.phase_id)
        if phase and phase.project_id == project_id:
            return phase
        return None

    phase_title = get_effective_phase_title(task)
    if not phase_title:
        return None

    normalized_title = _normalize_phase_title(phase_title)
    matches = [
        phase
        for phase in Phase.list_by_project(project_id)
        if _normalize_phase_title(phase.title) == normalized_title
    ]
    return matches[0] if len(matches) == 1 else None


def is_same_phase(task_1: Task, task_2: Task) -> bool:
    """Return whether two tasks belong to the same effective phase."""
    if task_1.phase_id and task_2.phase_id:
        return task_1.phase_id == task_2.phase_id
    return get_effective_phase_title(task_1) == get_effective_phase_title(task_2)


def select_task_to_start(project_id: str) -> tuple[Task | None, bool]:
    """Select the next task to start or resume based on workflow priority rules."""
    phases = Phase.list_by_project(project_id)
    active_phase = next((phase for phase in phases if phase.status == "active"), None)
    tasks = Task.list_by_project(project_id)

    if active_phase:
        in_progress_active = [
            task
            for task in tasks
            if task.status in {"in_progress", "in-progress"}
            and task_matches_phase(task, active_phase)
        ]
        if in_progress_active:
            return in_progress_active[0], True

        next_active = Task.get_next_for_phase(project_id, active_phase.id, active_phase.title)
        if next_active:
            return next_active, False

        next_unphased = Task.get_next_unphased(project_id)
        if next_unphased:
            return next_unphased, False

        in_progress_any = [task for task in tasks if task.status in {"in_progress", "in-progress"}]
        if in_progress_any:
            return in_progress_any[0], True

        return Task.get_next(project_id), False

    in_progress_any = [task for task in tasks if task.status in {"in_progress", "in-progress"}]
    if in_progress_any:
        return in_progress_any[0], True

    return Task.get_next(project_id), False


def is_draft_only_pending(project_id: str) -> bool:
    """Return True when remaining pending work is draft-only."""
    counts = Task.count_by_status(project_id)
    draft = counts.get("draft", 0)
    open_count = counts.get("open", 0) + counts.get("ready", 0) + counts.get("todo", 0)
    in_progress = counts.get("in-progress", 0) + counts.get("in_progress", 0)
    pending = sum(count for status, count in counts.items() if status not in ("done", "cancelled"))
    return draft > 0 and open_count == 0 and in_progress == 0 and draft == pending


def resolve_commit_type(task: Task, requested_type: str | None, allowed_types: set[str]) -> str:
    """Resolve the commit type from explicit input or task tags."""
    if requested_type:
        resolved = requested_type.lower()
        if resolved not in allowed_types:
            raise ValueError(requested_type)
        return resolved

    tag_to_type = {
        "bug": "fix",
        "bugfix": "fix",
        "fix": "fix",
        "docs": "docs",
        "documentation": "docs",
        "chore": "chore",
        "refactor": "refactor",
        "test": "test",
        "testing": "test",
        "ci": "ci",
        "style": "style",
        "perf": "perf",
        "feat": "feat",
        "feature": "feat",
    }

    for tag in task.tags:
        cleaned_tag = tag.strip().lower()
        if cleaned_tag in allowed_types:
            return cleaned_tag
        if cleaned_tag in tag_to_type:
            return tag_to_type[cleaned_tag]

    return "feat"
