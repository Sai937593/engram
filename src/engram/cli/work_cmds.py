"""Core workflow commands: start and finish."""

import subprocess

import click

import engram.cli as cli_root
import engram.context_helpers.startup as startup_context
from engram.cli.work_cmds_helpers import (
    format_retrieval_debug_output,
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
from engram.models.task import Task, get_effective_phase_title


def _filter_git_output(output: str | None) -> str:
    """Remove noisy git line-ending warnings while preserving actionable output."""
    if not output:
        return ""

    filtered_lines = []
    for line in output.splitlines():
        normalized = line.lower()
        is_line_ending_warning = (
            "warning:" in normalized
            and "working copy" in normalized
            and "will be replaced by" in normalized
            and "lf" in normalized
            and "crlf" in normalized
        )
        if not is_line_ending_warning:
            filtered_lines.append(line)
    return "\n".join(filtered_lines)


def _print_filtered_git_output(stdout: str | None, stderr: str | None) -> None:
    """Print filtered git output if any actionable lines remain."""
    for output in (_filter_git_output(stdout), _filter_git_output(stderr)):
        if output:
            cli_root.console.print(output)


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
            cli_root.console.print("\n" + format_retrieval_debug_output(startup_task_memory_result))
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
        cli_root.console.print("\n" + format_retrieval_debug_output(startup_task_memory_result))
    cli_root.console.print("=" * 40 + "\n")


@cli_root.cli.command(name="finish")
@click.option(
    "-t",
    "--type",
    "commit_type",
    default=None,
    help="Conventional commit type (e.g. feat, fix, docs)",
)
def finish(commit_type: str | None) -> None:
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

    cli_root.console.print("Step 1/4: Staging changes...")
    add_res = subprocess.run(["git", "add", "-A"], capture_output=True, text=True, check=False)
    if add_res.returncode != 0:
        cli_root.console.print("[red]Git staging failed. Fix errors and retry.[/red]")
        _print_filtered_git_output(add_res.stdout, add_res.stderr)
        return

    commit_msg = f"{resolved_type}({slugify(get_effective_phase_title(task)) or 'misc'}): {task.title} [{task.id}]"
    cli_root.console.print("Step 2/4: Creating commit...")
    commit_res = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)

    if commit_res.returncode != 0:
        if "nothing to commit" in commit_res.stdout:
            cli_root.console.print("[yellow]Nothing to commit. Proceeding...[/yellow]")
        else:
            cli_root.console.print("[red]Commit failed. Fix errors and retry.[/red]")
            _print_filtered_git_output(commit_res.stdout, commit_res.stderr)
            return

    cli_root.console.print("Step 3/4: Pushing branch...")
    push_res = subprocess.run(
        ["git", "push", "-u", "origin", "HEAD"], capture_output=True, text=True
    )
    if push_res.returncode != 0:
        cli_root.console.print("[red]Push failed. Pre-push hooks (tests) likely failed.[/red]")
        cli_root.console.print("Please fix the issues below and run `engram finish` again:")
        _print_filtered_git_output(push_res.stdout, push_res.stderr)
        return

    cli_root.console.print("Step 4/4: Marking task done...")
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
    cli_root.console.print("Review whether any project guardrails should be demoted.")
