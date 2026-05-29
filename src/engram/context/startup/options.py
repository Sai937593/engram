"""Configuration options and budget utilities for engram startup context."""

from __future__ import annotations

from dataclasses import dataclass

from engram.context.common import compact_text

TOKEN_TO_CHAR_APPROX = 4
STARTUP_TARGET_TOKEN_BUDGET_MIN = 1500
STARTUP_TARGET_TOKEN_BUDGET_MAX = 2000
STARTUP_HARD_TOKEN_BUDGET = 3000
STARTUP_TARGET_CHAR_BUDGET_MIN = STARTUP_TARGET_TOKEN_BUDGET_MIN * TOKEN_TO_CHAR_APPROX
STARTUP_TARGET_CHAR_BUDGET_MAX = STARTUP_TARGET_TOKEN_BUDGET_MAX * TOKEN_TO_CHAR_APPROX
STARTUP_HARD_CHAR_BUDGET = STARTUP_HARD_TOKEN_BUDGET * TOKEN_TO_CHAR_APPROX
CONTEXT_TRUNCATION_MARKER = "\n\n[Context truncated to fit budget.]"


@dataclass(frozen=True)
class StartupContextOptions:
    """Configuration for deterministic startup context rendering."""

    target_char_budget: int = STARTUP_TARGET_CHAR_BUDGET_MAX
    hard_char_budget: int = STARTUP_HARD_CHAR_BUDGET
    project_summary_char_limit: int = 400
    phase_text_char_limit: int = 400
    task_text_char_limit: int = 500
    guardrail_text_char_limit: int = 220
    task_memory_empty_state_text: str = "No relevant task memories selected."
    task_memory_empty_state_char_limit: int = 220
    task_memory_item_title_char_limit: int = 100
    task_memory_item_content_char_limit: int = 260
    l1_guardrail_limit: int = 6
    relevant_file_limit: int = 5
    relevant_file_path_char_limit: int = 120


def _compact_with_limit(text: str | None, char_limit: int) -> str:
    """Convert text to ASCII and truncate deterministically when needed."""
    compacted = compact_text(text)
    if not compacted or char_limit <= 0:
        return ""
    if len(compacted) <= char_limit:
        return compacted
    if char_limit <= 3:
        return compacted[:char_limit]
    return compacted[: char_limit - 3].rstrip() + "..."


def _enforce_hard_budget(rendered: str, hard_char_budget: int) -> str:
    """Cap output length with a deterministic truncation marker."""
    if hard_char_budget <= 0:
        return ""
    if len(rendered) <= hard_char_budget:
        return rendered

    if hard_char_budget <= len(CONTEXT_TRUNCATION_MARKER):
        return CONTEXT_TRUNCATION_MARKER[:hard_char_budget]

    visible = rendered[: hard_char_budget - len(CONTEXT_TRUNCATION_MARKER)].rstrip()
    return f"{visible}{CONTEXT_TRUNCATION_MARKER}"


def _render_section(title: str, lines: list[str]) -> str:
    """Render one startup section block."""
    rendered_lines = [f"## {title}"]
    rendered_lines.extend(line for line in lines if line)
    return "\n".join(rendered_lines)
