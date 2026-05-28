"""CLI-specific helper utilities for workflow behavior."""

from __future__ import annotations

import subprocess

from engram.memory_retrieval import StartupTaskMemoryRetrievalResult
from engram.models.phase import Phase
from engram.models.task import Task
from engram.services.workflow_helpers import get_target_branch


def format_retrieval_debug_output(result: StartupTaskMemoryRetrievalResult) -> str:
    """Render deterministic retrieval diagnostics for optional startup/command debugging."""
    query_text = result.query.query_text if result.query else ""
    retrieval = result.retrieval_metadata
    pack = result.pack_result.metadata
    selected_ids = ", ".join(item.memory_id for item in result.pack_result.items) or "(none)"
    selected_id_set = {item.memory_id for item in result.pack_result.items}
    hidden_ids = (
        ", ".join(
            candidate.memory_id
            for candidate in result.retrieval_candidates
            if candidate.memory_id not in selected_id_set
        )
        or "(none)"
    )
    empty_state_used = pack.selected_item_count == 0

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
        f"threshold_filtered_row_count={retrieval.threshold_filtered_row_count}, "
        f"threshold_filtered_task_scope_count={retrieval.threshold_filtered_task_scope_count}, "
        "threshold_filtered_project_scope_count="
        f"{retrieval.threshold_filtered_project_scope_count}",
        "scope channel metadata: "
        f"scanned_task_scope_row_count={retrieval.scanned_task_scope_row_count}, "
        f"scanned_project_scope_row_count={retrieval.scanned_project_scope_row_count}, "
        f"returned_task_scope_candidate_count={retrieval.returned_task_scope_candidate_count}, "
        "returned_project_scope_candidate_count="
        f"{retrieval.returned_project_scope_candidate_count}",
        "semantic index metadata: "
        f"semantic_status={retrieval.semantic_status}, "
        f"semantic_fallback_used={retrieval.semantic_fallback_used}, "
        f"semantic_reason={retrieval.semantic_reason or '(none)'}",
        "fusion metadata: "
        f"fused_returned_candidate_count={retrieval.returned_candidate_count}, "
        f"fts_returned_candidate_count={retrieval.fts_returned_candidate_count}, "
        f"semantic_returned_candidate_count={retrieval.semantic_returned_candidate_count}, "
        f"fused_duplicate_count={retrieval.fused_duplicate_count}, "
        f"exact_fts_preserved_count={retrieval.exact_fts_preserved_count}",
        "pack candidate metadata: "
        f"input_candidate_count={pack.input_candidate_count}, "
        f"unique_candidate_count={pack.unique_candidate_count}, "
        f"min_selection_boost_score={pack.min_selection_boost_score}, "
        f"relevance_filtered_count={pack.relevance_filtered_count}",
        "selected counts: "
        f"selected_item_count={pack.selected_item_count}, "
        f"hidden_item_count={pack.hidden_item_count}, "
        f"truncated_item_count={pack.truncated_item_count}",
        f"selected memory ids: {selected_ids}",
        f"hidden memory ids: {hidden_ids}",
        f"empty-state outcome: used_empty_state={empty_state_used}",
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


def get_active_phase(project_id: str) -> Phase | None:
    """Return the currently active phase for a project, if one exists."""
    phases = Phase.list_by_project(project_id)
    return next((phase for phase in phases if phase.status == "active"), None)
