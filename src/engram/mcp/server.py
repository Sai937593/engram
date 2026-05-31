"""STDIO bootstrap for the Engram MCP adapter."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from engram.db import init_db
from engram.mcp.resources import register_resources
from engram.mcp.tools import register_tools

SERVER_NAME = "engram"
MISSING_MCP_DEPENDENCY_MESSAGE = (
    'Missing optional MCP dependency. Install it with: uv pip install "engram[mcp]"'
)


def _load_fastmcp_class() -> type[Any]:
    """Load ``FastMCP`` from the optional MCP SDK."""
    try:
        fastmcp_module = import_module("mcp.server.fastmcp")
    except ModuleNotFoundError as exc:
        if exc.name and not exc.name.startswith("mcp"):
            raise
        raise RuntimeError(MISSING_MCP_DEPENDENCY_MESSAGE) from exc

    fastmcp_class = getattr(fastmcp_module, "FastMCP", None)
    if fastmcp_class is None:
        raise RuntimeError("Installed MCP SDK is missing mcp.server.fastmcp.FastMCP.")
    return fastmcp_class


def create_server() -> Any:
    """Create the MCP server skeleton with no tools/resources registered yet."""
    fastmcp_class = _load_fastmcp_class()
    server = fastmcp_class(SERVER_NAME)
    return server


def run_stdio_server() -> None:
    """Initialize Engram storage and run MCP over STDIO transport."""
    try:
        from engram.services.project_path import get_repo_local_db_path

        db_path = get_repo_local_db_path()
        if db_path.exists():
            init_db()
    except Exception:
        pass

    server = create_server()
    register_resources(server)
    register_tools(server)
    server.run(transport="stdio")


def main() -> None:
    """Console entrypoint for ``engram-mcp``."""
    try:
        run_stdio_server()
    except (RuntimeError, ModuleNotFoundError) as exc:
        import sys

        err_msg = str(exc)
        if (
            MISSING_MCP_DEPENDENCY_MESSAGE in err_msg
            or "Installed MCP SDK is missing" in err_msg
            or (isinstance(exc, ModuleNotFoundError) and exc.name and exc.name.startswith("mcp"))
        ):
            sys.stderr.write(f"Error: {err_msg}\n")
            sys.exit(1)
        raise
