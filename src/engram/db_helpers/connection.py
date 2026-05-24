"""Database connection helpers."""

import sqlite3
from pathlib import Path


def create_db_connection(db_path: Path) -> sqlite3.Connection:
    """Return a sqlite connection configured for Engram."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn
