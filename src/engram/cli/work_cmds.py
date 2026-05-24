"""Core workflow commands: start and finish."""

import subprocess

import click

import engram.cli as cli_root
from engram.cli.work_cmds_helpers import (
    get_current_branch,
    get_target_branch,
    git_checkout_phase_branch,
    is_same_phase,
    is_working_tree_dirty,
    resolve_commit_type,
    select_task_to_start,
    slugify,
)
from engram.context import get_task_context
from engram.models.task import Task, get_effective_phase_title


@cli_root.cli.command(name="start")
def start():
    """Start the next task in the workflow."""
    project = cli_root.get_current_project()
    task, is_resuming = select_task_to_start(project.id)

    if not task:
        counts = Task.count_by_status(project.id)
        total = sum(counts.values())
        if total == 0:
            cli_root.console.print(
                "[yellow]No tasks defined.[/yellow] The next phase has not been planned yet."
            )
            cli_root.console.print(
                "Action: Ask the user what the next phase of work should be, then run:"
            )
            cli_root.console.print(
                '  [cyan]engram task add "<task title>" --phase "Phase N" --priority high[/cyan]'
            )
        elif all(status in ("done", "cancelled") for status in counts):
            cli_root.console.print("[green]All tasks complete.[/green] This project is done.")
            cli_root.console.print(
                "Action: Confirm with the user whether to plan the next phase or close the project."
            )
        else:
            blocked = counts.get("blocked", 0)
            cli_root.console.print(
                f"[red]All remaining tasks are blocked[/red] ({blocked} blocked)."
            )
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

    context_str = get_task_context(task.id, hard_constraints_only=True)
    cli_root.console.print("\n" + "=" * 40)
    cli_root.console.print(context_str)
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
