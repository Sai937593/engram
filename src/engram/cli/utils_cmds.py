"""Utility commands for commit validation and packaged guide access."""

import re
from importlib import resources

import click
from rich.markdown import Markdown

import engram.cli as cli_root


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


@cli_root.cli.command(name="db")
def db() -> None:
    """Show database path, size, and health status."""
    from engram.db import DEFAULT_DB_PATH, get_db_connection

    cli_root.console.print(f"[cyan]Database Path:[/cyan] {DEFAULT_DB_PATH}")
    exists = DEFAULT_DB_PATH.exists()
    cli_root.console.print(f"[cyan]Database Exists:[/cyan] {'Yes' if exists else 'No'}")

    if exists:
        try:
            size_kb = DEFAULT_DB_PATH.stat().st_size / 1024
            cli_root.console.print(f"[cyan]Database Size:[/cyan] {size_kb:.2f} KB")
        except Exception as e:
            cli_root.console.print(f"[red]Error reading size:[/red] {str(e)}")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        status = cursor.fetchone()[0]
        conn.close()
        if status == "ok":
            cli_root.console.print("[green]Database Connection & Integrity: Healthy[/green]")
        else:
            cli_root.console.print(f"[red]Database Integrity Warning:[/red] {status}")
    except Exception as e:
        cli_root.console.print(f"[red]Database Connection Error:[/red] {str(e)}")
