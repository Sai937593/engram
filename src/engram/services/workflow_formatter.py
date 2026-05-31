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
    relevant_files: list[str] | None,
    guardrails: list[str] | None,
    memories: list[str] | None,
    next_action: str | None,
) -> str:
    """Format a compact Work Order as a Markdown-first string."""
    lines = ["# Work Order", ""]
    lines.append(f"Status: {status}")
    if task_id and task_title:
        lines.append(f"Task: `{task_id}` — {task_title}")
    elif task_id:
        lines.append(f"Task: `{task_id}`")

    if phase_title and phase_id:
        lines.append(f"Phase: {phase_title} ({phase_id})")
    elif phase_title:
        lines.append(f"Phase: {phase_title}")

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

    if relevant_files:
        lines.append("## Start here")
        for f in relevant_files:
            lines.append(f"- {f}")
        lines.append("")

    if guardrails:
        lines.append("## Guardrails")
        for g in guardrails:
            lines.append(f"- {g}")
        lines.append("")

    if memories:
        lines.append("## Relevant memory")
        for m in memories:
            lines.append(f"- {m}")
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
        lines.append(f"Task: `{task_id}` — {task_title}")
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
        lines.append(f"Task: `{task_id}` — {task_title}")
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
) -> str:
    """Format a successful finish response as a Markdown-first string."""
    lines = ["# Task Finished", ""]
    if task_title:
        lines.append(f"Task: `{task_id}` — {task_title}")
    else:
        lines.append(f"Task: `{task_id}`")
    lines.append(f"Commit: `{commit_msg}`")
    lines.append(f"Phase complete: {phase_complete}")
    lines.append("")
    lines.append("## Next action")
    lines.append(next_guidance)
    lines.append("")
    return "\n".join(lines).strip() + "\n"
