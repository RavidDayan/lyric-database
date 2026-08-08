"""SQLite connection handling and schema management."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import config


def connect(db_path: Path | str) -> sqlite3.Connection:
    db_path = Path(db_path)
    if db_path.parent and str(db_path) != ":memory:":
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def read_schema_sql() -> str:
    return config.SCHEMA_PATH.read_text(encoding="utf-8")


def create_schema(conn: sqlite3.Connection) -> None:
    """Create every table and index from the frozen Stage A DDL."""
    conn.executescript(read_schema_sql())
    conn.execute("PRAGMA foreign_keys = ON")


def drop_all_objects(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    names = [
        (row["type"], row["name"])
        for row in conn.execute(
            "SELECT type, name FROM sqlite_master "
            "WHERE type IN ('table', 'index', 'view', 'trigger') "
            "AND name NOT LIKE 'sqlite_%'"
        )
    ]
    for obj_type, name in names:
        if obj_type == "index" and name.startswith("sqlite_autoindex"):
            continue
        conn.execute(f'DROP {obj_type} IF EXISTS "{name}"')
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


def reset_database(conn: sqlite3.Connection) -> None:
    """Return an open connection to an empty, freshly created schema."""
    drop_all_objects(conn)
    create_schema(conn)
    conn.commit()


def open_database(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open the database, creating the schema when the file is new."""
    db_path = Path(db_path) if db_path is not None else config.DATABASE_PATH
    conn = connect(db_path)
    has_tables = conn.execute(
        "SELECT COUNT(*) AS n FROM sqlite_master "
        "WHERE type = 'table' AND name = 'document'"
    ).fetchone()["n"]
    if not has_tables:
        create_schema(conn)
        conn.commit()
    return conn


def table_counts(conn: sqlite3.Connection, tables: list[str]) -> dict[str, int]:
    return {
        table: conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        for table in tables
    }
