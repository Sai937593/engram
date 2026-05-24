"""Core workflow commands: start and finish."""

import subprocess

import click

import engram.cli as cli_root
import engram.context_helpers.startup as startup_context
from engram.cli.work_cmds_helpers import (
    get_active_phase,
    get_current_branch,
    get_target_branch,
    git_checkout_phase_branch,
    is_same_phase,
    is_working_tree_dirty,
    resolve_commit_type,
    select_task_to_start,
    slugify,
)
from engram.memory_retrieval import StartupTaskMemoryRetrievalResult
from engram.models.task import Task, get_effective_phase_title


def _format_retrieval_debug_output(result: StartupTaskMemoryRetrievalResult) -> str:
    """Render deterministic retrieval diagnostics for optional startup debugging."""
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


@cli_root.cli.command(name="start")
@click.option(
    "--debug-retrieval",
    is_flag=True,
    default=False,
    help="Print retrieval query, candidate, and packing diagnostics.",
)
def start(debug_retrieval: bool):
    """Start the next task in the workflow."""
    project = cli_root.get_current_project()
    active_phase = get_active_phase(project.id)
    task, is_resuming = select_task_to_start(project.id)

    if not task:
        startup_task_memory_result = startup_context.orchestrate_startup_task_memory_retrieval(
            project=project,
            active_phase=active_phase,
            selected_task=None,
        )
        context_str = startup_context.build_startup_context(
            project=project,
            active_phase=active_phase,
            selected_task=None,
            startup_task_memory_result=startup_task_memory_result,
        )
        cli_root.console.print("\n" + "=" * 40)
        cli_root.console.print(context_str)
        if debug_retrieval:
            cli_root.console.print(
                "\n" + _format_retrieval_debug_output(startup_task_memory_result)
            )
        cli_root.console.print("=" * 40 + "\n")
        return

    target_branch = get_target_branch(task)
    current_branch = get_current_branch()
    if current_branch != target_branch and is_working_tree_dirty():
        cli_root.console.print(
            f"[red]Error:[/red] Git working tree is dirty, and starting this task requires checking out branch "
            f"[cyan]{target_branch}[/cyan] (current branch is [cyan]{current_branch or 'unknown'}[/cyan])."
        )
        cli_root.console.print("Please commit or stash your changes before starting a task.")
        raise SystemExit(1)

    if is_resuming:
        cli_root.console.print(f"[yellow]Resuming in-progress task:[/yellow] {task.id}")
    else:
        task.update(status="in-progress")
        cli_root.console.print(f"[green]Started task:[/green] {task.id}")

    git_checkout_phase_branch(task)

    startup_task_memory_result = startup_context.orchestrate_startup_task_memory_retrieval(
        project=project,
        active_phase=active_phase,
        selected_task=task,
    )
    context_str = startup_context.build_startup_context(
        project=project,
        active_phase=active_phase,
        selected_task=task,
        startup_task_memory_result=startup_task_memory_result,
    )
    cli_root.console.print("\n" + "=" * 40)
    cli_root.console.print(context_str)
    if debug_retrieval:
        cli_root.console.print("\n" + _format_retrieval_debug_output(startup_task_memory_result))
    cli_root.console.print("=" * 40 + "\n")


@cli_root.cli.command(name="finish")
@click.option(
    "-t",
    "--type",
    "commit_type",
    default=None,
    help="Conventional commit type (e.g. feat, fix, docs)",
)
def finish(commit_type):
    """Finish the active task (commit, push, and mark done)."""
    project = cli_root.get_current_project()
    tasks = Task.list_by_project(project.id)
    in_progress = [task for task in tasks if task.status == "in-progress"]

    if not in_progress:
        cli_root.console.print("[red]Error:[/red] No task is currently in-progress.")
        return

    task = in_progress[0]

    try:
        resolved_type = resolve_commit_type(task, commit_type, cli_root.CONVENTIONAL_COMMIT_TYPES)
    except ValueError:
        cli_root.console.print(f"[red]Error:[/red] Invalid commit type '{commit_type}'.")
        cli_root.console.print(
            f"Must be one of: {', '.join(sorted(cli_root.CONVENTIONAL_COMMIT_TYPES))}"
        )
        raise SystemExit(1) from None

    cli_root.console.print(f"Finishing task: {task.title} ({task.id})")

    subprocess.run(["git", "add", "-A"], check=False)

    commit_msg = f"{resolved_type}({slugify(get_effective_phase_title(task)) or 'misc'}): {task.title} [{task.id}]"
    commit_res = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)

    if commit_res.returncode != 0:
        if "nothing to commit" in commit_res.stdout:
            cli_root.console.print("[yellow]Nothing to commit. Proceeding...[/yellow]")
        else:
            cli_root.console.print("[red]Commit failed. Fix errors and retry.[/red]")
            cli_root.console.print(commit_res.stdout)
            cli_root.console.print(commit_res.stderr)
            return

    push_res = subprocess.run(
        ["git", "push", "-u", "origin", "HEAD"], capture_output=True, text=True
    )
    if push_res.returncode != 0:
        cli_root.console.print("[red]Push failed. Pre-push hooks (tests) likely failed.[/red]")
        cli_root.console.print("Please fix the issues below and run `engram finish` again:")
        cli_root.console.print(push_res.stdout)
        cli_root.console.print(push_res.stderr)
        return

    task.update(status="done")
    cli_root.console.print(f"[green]Task '{task.id}' marked as done.[/green]")

    next_task = Task.get_next(project.id)
    if not next_task or not is_same_phase(next_task, task):
        phase_tasks = [phase_task for phase_task in tasks if is_same_phase(phase_task, task)]
        if all(phase_task.status in ("done", "cancelled") for phase_task in phase_tasks):
            cli_root.console.print("\n[bold green]Phase Complete![/bold green]")
            cli_root.console.print("All tasks in the current phase are done.")
            cli_root.console.print(
                "Please ask the user for permission to create a PR and merge this phase."
            )
