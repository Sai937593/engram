"""Local read-only UI command."""

import click

import engram.cli as cli_root
from engram.ui.app import create_app


@cli_root.cli.command(name="ui")
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind.")
@click.option("--port", default=8765, show_default=True, type=int, help="Port to bind.")
def ui(host: str, port: int) -> None:
    """Serve the read-only local inspection UI for the current project."""
    try:
        import uvicorn
    except ImportError as exc:
        raise click.ClickException("Install UI dependencies first: uv sync --extra ui") from exc

    project = cli_root.get_current_project()
    app = create_app(project.id)
    url = f"http://{host}:{port}"
    cli_root.console.print(f"[green]Engram UI:[/green] {project.name} -> {url}")
    uvicorn.run(app, host=host, port=port)
