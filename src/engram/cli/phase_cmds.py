"""Phase command group registration."""

import engram.cli as cli_root


@cli_root.cli.group()
def phase() -> None:
    """Manage phases."""
    pass
