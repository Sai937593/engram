"""Shared formatter for Markdown-first workflow responses."""

from __future__ import annotations


def format_work_order(
    status: str,
    task_id: str | None,
    task_title: str | None,
    phase_title: str | None,
    phase_id: str | None,
    branch: str | None,
    objective: str | None,
    acceptance: str | None,
    task_context: list[str] | None,
    relevant_files: list[str] | None,
    start_hints: list[str] | None,
    guardrails: list[str] | None,
    memories: list[str] | None,
    next_action: str | None,
) -> str:
    """Format a compact Work Order as a Markdown-first string."""
    lines = ["# Work Order", ""]
    if branch:
        lines.append(f"Branch: `{branch}`")
        lines.append("")

    if objective:
        lines.append("## Objective")
        lines.append(objective)
        lines.append("")

    if acceptance:
        lines.append("## Acceptance")
        lines.append(acceptance)
        lines.append("")

    if task_context:
        lines.append("## Task context")
        for entry in task_context:
            lines.append(f"- {entry}")
        lines.append("")

    lines.append("## Start here")
    if relevant_files:
        for f in relevant_files:
            lines.append(f"- {f}")
    else:
        lines.append(
            "- Search the codebase using engram_memory_search to find relevant memories or context."
        )
        if start_hints:
            for hint in start_hints:
                lines.append(f"- Search hint: {hint}")
    lines.append("")

    lines.append("## Guardrails")
    if guardrails:
        for g in guardrails:
            # Ensure we don't double-prepend hyphens if the builder already added them
            line_str = g if g.startswith("- ") else f"- {g}"
            lines.append(line_str)
    else:
        lines.append("- Keep non-test Python files within structure limits.")
    lines.append("")

    lines.append("## Boundaries")
    lines.append(
        "- No-touch folders: Do not edit, create, or delete files inside planning/, workflow/, or .github/ directories."
    )
    lines.append(
        "- CLI boundary: Services under `src/engram/services` must not import Click, Rich, CLI command modules, subprocess, or MCP adapter code."
    )
    lines.append("")

    lines.append("## Required gates")
    lines.append(
        "- Pre-coding: Create `implementation_plan.md` and await user approval before writing code."
    )
    lines.append(
        "- Pre-commit: Rerun unit tests and ensure zero failures before invoking `engram_workflow_finish`."
    )
    lines.append("")

    if memories:
        lines.append("## Relevant memory")
        for m in memories:
            line_str = m if m.startswith("- ") else f"- {m}"
            lines.append(line_str)
        lines.append("")

    if next_action:
        lines.append("## Next action")
        lines.append(next_action)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def format_start_blocked(reason: str, next_guidance: str) -> str:
    """Format a blocked start response as a Markdown-first string."""
    lines = [
        "# Start Blocked",
        "",
        f"Reason: {reason}",
        "",
        "## Next action",
        next_guidance,
        "",
    ]
    return "\n".join(lines).strip() + "\n"


def format_verify_result(
    task_id: str,
    passed: bool,
    details: str,
    next_guidance: str,
    task_title: str | None = None,
) -> str:
    """Format a verification result as a Markdown-first string."""
    status = "PASSED" if passed else "FAILED"
    lines = ["# Verification Result", ""]
    if task_title:
        lines.append(f"Task: `{task_id}` - {task_title}")
    else:
        lines.append(f"Task: `{task_id}`")
    lines.append(f"Status: {status}")
    lines.append("")
    lines.append("## Details")
    lines.append(details)
    lines.append("")
    lines.append("## Next action")
    lines.append(next_guidance)
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def format_finish_blocked(
    task_id: str,
    reason: str,
    next_guidance: str,
    task_title: str | None = None,
) -> str:
    """Format a blocked finish response as a Markdown-first string."""
    lines = ["# Finish Blocked", ""]
    if task_title:
        lines.append(f"Task: `{task_id}` - {task_title}")
    else:
        lines.append(f"Task: `{task_id}`")
    lines.append(f"Reason: {reason}")
    lines.append("")
    lines.append("## Next action")
    lines.append(next_guidance)
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def format_finish_success(
    task_id: str,
    commit_msg: str,
    phase_complete: bool,
    next_guidance: str,
    task_title: str | None = None,
    memory_review_outcome: str | None = None,
) -> str:
    """Format a successful finish response as a Markdown-first string."""
    lines = ["# Task Finished", ""]
    if task_title:
        lines.append(f"Task: `{task_id}` - {task_title}")
    else:
        lines.append(f"Task: `{task_id}`")
    lines.append(f"Commit: `{commit_msg}`")
    lines.append(f"Phase complete: {phase_complete}")
    if memory_review_outcome:
        lines.append(f"Memory review outcome: `{memory_review_outcome}`")
    lines.append("")
    lines.append("## Next action")
    lines.append(next_guidance)
    lines.append("")
    return "\n".join(lines).strip() + "\n"
