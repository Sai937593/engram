import sys
from unittest.mock import MagicMock


def test_mcp_main_execution(monkeypatch):
    """Verify that python -m engram.mcp calls the server main function."""
    mock_main = MagicMock()
    monkeypatch.setattr("engram.mcp.server.main", mock_main)

    # We must remove it from sys.modules if it was already imported
    # so that the code inside __main__.py actually runs again.
    if "engram.mcp.__main__" in sys.modules:
        del sys.modules["engram.mcp.__main__"]

    import engram.mcp.__main__  # noqa: F401

    mock_main.assert_called_once()
