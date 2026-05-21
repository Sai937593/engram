"""Core workflow commands: start and finish."""

import re
import subprocess

import click

import engram.cli as cli_root
from engram.context import get_task_context
from engram.models.task import Task


def slugify(text: str) -> str:
    if not text:
        return "misc"
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def git_checkout_phase_branch(phase: str) -> None:
    slug = slugify(phase)
    branch_name = f"feat/phase-{slug}"

    # Check if branch exists
    result = subprocess.run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"])
    if result.returncode == 0:
        # Branch exists, just checkout
        subprocess.run(["git", "checkout", branch_name], check=False)
    else:
        # Check if we are on main, if not, maybe we should checkout main first?
        # Actually just create it from current branch (assume main or previous phase).
        # We will do checkout -b
        subprocess.run(["git", "checkout", "-b", branch_name], check=False)


def is_working_tree_dirty() -> bool:
    """Return True if there are uncommitted changes in the git repository."""
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if res.returncode != 0:
        return False
    return bool(res.stdout.strip())


def get_current_branch() -> str:
    """Return the name of the current active git branch."""
    res = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True
    )
    if res.returncode != 0:
        return ""
    return res.stdout.strip()


@cli_root.cli.command(name="start")
def start():
    """Start the next task in the workflow."""
    p = cli_root.get_current_project()
    t = Task.get_next(p.id)

    # Are there any in-progress tasks we should resume?
    tasks = Task.list_by_project(p.id)
    in_progress = [task for task in tasks if task.status == "in-progress"]

    if in_progress:
        t = in_progress[0]
    elif not t:
        # No task available
        counts = Task.count_by_status(p.id)
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
        elif all(s in ("done", "cancelled") for s in counts):
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

    # Check git status before branch checkout safely
    if t.phase:
        target_branch = f"feat/phase-{slugify(t.phase)}"
        current_branch = get_current_branch()
        if current_branch != target_branch and is_working_tree_dirty():
            cli_root.console.print(
                f"[red]Error:[/red] Git working tree is dirty, and starting this task requires checking out branch "
                f"[cyan]{target_branch}[/cyan] (current branch is [cyan]{current_branch or 'unknown'}[/cyan])."
            )
            cli_root.console.print("Please commit or stash your changes before starting a task.")
            raise SystemExit(1)

    if in_progress:
        cli_root.console.print(f"[yellow]Resuming in-progress task:[/yellow] {t.id}")
    else:
        t.update(status="in-progress")
        cli_root.console.print(f"[green]Started task:[/green] {t.id}")

    # We have a task, check out phase branch
    if t.phase:
        git_checkout_phase_branch(t.phase)

    # Print the rich context
    context_str = get_task_context(t.id)
    # Also print the global rules if we want, or just rely on get_task_context which includes PROJECT KNOWLEDGE
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
    p = cli_root.get_current_project()
    tasks = Task.list_by_project(p.id)
    in_progress = [t for t in tasks if t.status == "in-progress"]

    if not in_progress:
        cli_root.console.print("[red]Error:[/red] No task is currently in-progress.")
        return

    t = in_progress[0]

    # Validate or resolve commit type
    resolved_type = None
    if commit_type:
        resolved_type = commit_type.lower()
        if resolved_type not in cli_root.CONVENTIONAL_COMMIT_TYPES:
            cli_root.console.print(f"[red]Error:[/red] Invalid commit type '{commit_type}'.")
            cli_root.console.print(
                f"Must be one of: {', '.join(sorted(cli_root.CONVENTIONAL_COMMIT_TYPES))}"
            )
            raise SystemExit(1)
    else:
        # Auto-resolve from tags
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
        for tag in t.tags:
            cleaned_tag = tag.strip().lower()
            if cleaned_tag in cli_root.CONVENTIONAL_COMMIT_TYPES:
                resolved_type = cleaned_tag
                break
            if cleaned_tag in tag_to_type:
                resolved_type = tag_to_type[cleaned_tag]
                break

        if not resolved_type:
            resolved_type = "feat"

    cli_root.console.print(f"Finishing task: {t.title} ({t.id})")

    # Git operations
    subprocess.run(["git", "add", "-A"], check=False)

    commit_msg = f"{resolved_type}({slugify(t.phase) or 'misc'}): {t.title} [{t.id}]"
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

    # Tests passed, push succeeded, mark done
    t.update(status="done")
    cli_root.console.print(f"[green]Task '{t.id}' marked as done.[/green]")

    # Check if phase is complete
    next_t = Task.get_next(p.id)
    if not next_t or next_t.phase != t.phase:
        # Either no more tasks, or the next task is in a different phase
        # Check if all tasks in CURRENT phase are done
        phase_tasks = [pt for pt in tasks if pt.phase == t.phase]
        if all(pt.status in ("done", "cancelled") for pt in phase_tasks):
            cli_root.console.print("\n[bold green]Phase Complete![/bold green]")
            cli_root.console.print("All tasks in the current phase are done.")
            cli_root.console.print(
                "Please ask the user for permission to create a PR and merge this phase."
            )
