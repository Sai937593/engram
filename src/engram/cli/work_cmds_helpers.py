"""Helper utilities for workflow command behavior."""

from __future__ import annotations

import re
import subprocess

from engram.cli.phase_helpers import normalize_phase_title
from engram.memory_retrieval import StartupTaskMemoryRetrievalResult
from engram.models.phase import Phase
from engram.models.task import Task, get_effective_phase_title


def format_retrieval_debug_output(result: StartupTaskMemoryRetrievalResult) -> str:
    """Render deterministic retrieval diagnostics for optional startup/command debugging."""
    query_text = result.query.query_text if result.query else ""
    retrieval = result.retrieval_metadata
    pack = result.pack_result.metadata
    selected_ids = ", ".join(item.memory_id for item in result.pack_result.items) or "(none)"

    lines = [
        "## RETRIEVAL DEBUG",
        f"query text: {query_text or '(empty)'}",
        f"retrieval mode: {retrieval.source}",
        "fts candidate metadata: "
        f"max_candidates={retrieval.max_candidates}, "
        f"scanned_row_count={retrieval.scanned_row_count}, "
        f"returned_candidate_count={retrieval.returned_candidate_count}",
        "lexical threshold metadata: "
        "min_content_term_hits_without_title_or_tag="
        f"{retrieval.threshold_min_content_term_hits_without_title_or_tag}, "
        f"threshold_filtered_row_count={retrieval.threshold_filtered_row_count}",
        "pack candidate metadata: "
        f"input_candidate_count={pack.input_candidate_count}, "
        f"unique_candidate_count={pack.unique_candidate_count}",
        "selected counts: "
        f"selected_item_count={pack.selected_item_count}, "
        f"hidden_item_count={pack.hidden_item_count}, "
        f"truncated_item_count={pack.truncated_item_count}",
        f"selected memory ids: {selected_ids}",
        "budget usage: "
        f"used_char_count={pack.used_char_count}/{pack.section_char_budget}, "
        f"section_budget_exhausted={pack.section_budget_exhausted}",
    ]
    if retrieval.fallback_reason:
        lines.append(f"fallback reason: {retrieval.fallback_reason}")
    elif retrieval.fallback_used:
        lines.append("fallback reason: (none provided)")

    if result.pack_result.items:
        lines.append("selected item metadata:")
        for item in result.pack_result.items:
            lines.append(
                f"- memory_id={item.memory_id}, retrieval_source={item.retrieval_source}, "
                f"fts_rank={item.fts_rank:.6f}, boost_score={item.boost_score}, "
                f"source_candidate_index={item.source_candidate_index}, "
                f"char_count={item.char_count}, was_truncated={item.was_truncated}"
            )

    return "\n".join(lines)


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


def git_checkout_phase_branch(task: Task) -> None:
    """Check out the git branch corresponding to the task's effective phase."""
    branch_name = get_target_branch(task)

    result = subprocess.run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"])
    if result.returncode == 0:
        subprocess.run(["git", "checkout", branch_name], check=False)
        return

    subprocess.run(["git", "checkout", "-b", branch_name], check=False)


def is_working_tree_dirty() -> bool:
    """Return True when uncommitted changes are present in the repository."""
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if res.returncode != 0:
        return False
    return bool(res.stdout.strip())


def get_current_branch() -> str:
    """Return the current git branch name, or an empty string on failure."""
    res = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True
    )
    if res.returncode != 0:
        return ""
    return res.stdout.strip()


def task_matches_phase(task: Task, phase: Phase) -> bool:
    """Return whether a task is linked to a phase via first-class or legacy data."""
    if task.phase_id == phase.id:
        return True
    if task.phase_id:
        return False
    return normalize_phase_title(task.phase) == normalize_phase_title(phase.title)


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
            if task.status == "in-progress" and task_matches_phase(task, active_phase)
        ]
        if in_progress_active:
            return in_progress_active[0], True

        next_active = Task.get_next_for_phase(project_id, active_phase.id, active_phase.title)
        if next_active:
            return next_active, False

        next_unphased = Task.get_next_unphased(project_id)
        if next_unphased:
            return next_unphased, False

        in_progress_any = [task for task in tasks if task.status == "in-progress"]
        if in_progress_any:
            return in_progress_any[0], True

        return Task.get_next(project_id), False

    in_progress_any = [task for task in tasks if task.status == "in-progress"]
    if in_progress_any:
        return in_progress_any[0], True

    return Task.get_next(project_id), False


def get_active_phase(project_id: str) -> Phase | None:
    """Return the currently active phase for a project, if one exists."""
    phases = Phase.list_by_project(project_id)
    return next((phase for phase in phases if phase.status == "active"), None)


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
