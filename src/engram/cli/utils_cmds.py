"""Utility commands for commit validation and packaged guide access."""

import re
import subprocess
from importlib import resources

import click
from rich.markdown import Markdown

import engram.cli as cli_root


@cli_root.cli.command(name="commit")
@click.option("-m", "--message", required=True, help="Commit message (Conventional Commits format)")
@click.option(
    "--no-validate", is_flag=True, default=False, help="Skip commit message format validation"
)
def commit(message: str, no_validate: bool) -> None:
    """Atomic commit: stage all, validate message, commit (pre-commit hooks run automatically)."""
    if not no_validate:
        pattern = rf"^({'|'.join(cli_root.CONVENTIONAL_COMMIT_TYPES)})(\(.+\))?: .+"
        if not re.match(pattern, message):
            cli_root.console.print(
                "[red]Error:[/red] Commit message does not follow Conventional Commits format."
            )
            cli_root.console.print("  Expected: [cyan]type(scope): description[/cyan]")
            cli_root.console.print(
                f"  Types: {', '.join(sorted(cli_root.CONVENTIONAL_COMMIT_TYPES))}"
            )
            cli_root.console.print("  Example: [cyan]feat(cli): add lesson command [T-001][/cyan]")
            return
        if "[" not in message:
            cli_root.console.print(
                "[yellow]Warning:[/yellow] No task ID found in message. Recommended: add [task-id]"
            )

    cli_root.console.print("[dim]Staging all changes...[/dim]")
    result = subprocess.run(["git", "add", "-A"], capture_output=True, text=True)
    if result.returncode != 0:
        cli_root.console.print(f"[red]git add failed:[/red] {result.stderr.strip()}")
        return

    cli_root.console.print("[dim]Committing... (pre-commit hooks will run if installed)[/dim]")
    result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
    if result.returncode != 0:
        cli_root.console.print(
            f"[red]Commit failed:[/red]\n{result.stdout.strip()}\n{result.stderr.strip()}"
        )
        return

    hash_result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
    )
    commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else "unknown"
    cli_root.console.print(f"[green]Committed:[/green] {commit_hash}  {message}")


@cli_root.cli.command(name="guide")
@click.argument("section", required=False)
def guide(section):
    """Show the User Manual. Optional: provide a section (concepts, commands, workflow, troubleshooting)."""
    try:
        pkg = resources.files("engram")
        content = (pkg / "USER_MANUAL.md").read_text(encoding="utf-8")
    except Exception as e:
        cli_root.console.print(f"[red]Error reading manual:[/red] {str(e)}")
        return

    if section:
        section = section.lower()
        mapping = {
            "concepts": "## 1. Core Concepts",
            "commands": "## 2. Command Reference",
            "workflow": "## 3. Recommended Agent Workflow",
            "troubleshooting": "## 4. Troubleshooting",
        }

        header = mapping.get(section)
        if header:
            parts = re.split(r"(\n##\s.*?\n|\n---)", content)
            found = False
            section_content = ""
            for i in range(len(parts)):
                if header in parts[i]:
                    found = True
                    section_content = parts[i] + (parts[i + 1] if i + 1 < len(parts) else "")
                    break

            if found:
                content = f"# Engram Guide: {section.capitalize()}\n\n" + section_content
            else:
                cli_root.console.print(f"[yellow]Section '{section}' not found.[/yellow]")
                return

    cli_root.console.print(Markdown(content))
