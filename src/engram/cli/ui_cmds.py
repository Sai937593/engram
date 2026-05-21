"""Local read-only UI command."""

import json
import socket
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import click

import engram.cli as cli_root
from engram.ui.app import create_app
from engram.ui.state import UiStateError, resolve_target_from_cwd, write_target


@cli_root.cli.command(name="ui")
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind.")
@click.option("--port", default=8765, show_default=True, type=int, help="Port to bind.")
def ui(host: str, port: int) -> None:
    """Serve the read-only local inspection UI for the current project."""
    try:
        target = resolve_target_from_cwd()
    except UiStateError as exc:
        raise click.ClickException(str(exc)) from exc

    url = f"http://{host}:{port}"
    if _is_port_open(host, port):
        running = _read_running_engram_ui(url)
        if not running:
            raise click.ClickException(
                f"{host}:{port} is already in use, but it is not a compatible Engram UI "
                "server. Stop that process or launch with --port <free-port>."
            )
        write_target(target)
        cli_root.console.print(
            f"[green]Engram UI updated:[/green] {target.project_name} "
            f"({target.project_id}) -> {url}"
        )
        cli_root.console.print(f"[dim]Repo:[/dim] {target.repo_path}")
        return

    try:
        _import_uvicorn()
    except ImportError as exc:
        raise click.ClickException("Install UI dependencies first: uv sync --extra ui") from exc

    write_target(target)
    app = create_app()
    cli_root.console.print(
        f"[green]Engram UI:[/green] {target.project_name} ({target.project_id}) -> {url}"
    )
    cli_root.console.print(f"[dim]Repo:[/dim] {target.repo_path}")
    _serve_app(app, host=host, port=port)


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except OSError:
        return False


def _read_running_engram_ui(url: str) -> dict | None:
    try:
        with urlopen(f"{url}/api/ui-state", timeout=1) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    if payload.get("app") != "engram-ui":
        return None
    return payload


def _import_uvicorn() -> None:
    import uvicorn  # noqa: F401


def _serve_app(app, host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)
