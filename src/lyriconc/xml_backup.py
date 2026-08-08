"""XML backup and restore - the additional topic of the project.

Export writes every project table to one XML file. Restore recreates the
database from the SQL DDL and re-inserts the rows in foreign-key-safe order, so
the SQL schema always stays the authoritative definition of the database.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from . import db

# Parents first, children after: this order is used for both export and import.
TABLE_ORDER = (
    "artist",
    "album",
    "document",
    "document_contributor",
    "stanza",
    "lyric_line",
    "word",
    "occurrence",
    "word_group",
    "word_group_member",
    "phrase",
    "phrase_word",
)


class XmlBackupError(RuntimeError):
    pass


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]


def export_database_xml(conn: sqlite3.Connection, output_path: Path | str) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    exported_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        handle.write(f'<lyriconcBackup exportedAt="{exported_at}">\n')
        for table in TABLE_ORDER:
            columns = _columns(conn, table)
            handle.write(f'  <table name="{table}">\n')
            for row in conn.execute(f"SELECT * FROM {table}"):
                handle.write("    <row>\n")
                for column in columns:
                    value = row[column]
                    if value is None:
                        handle.write(f'      <{column} null="true"/>\n')
                    else:
                        handle.write(
                            f"      <{column}>{escape(str(value))}</{column}>\n"
                        )
                handle.write("    </row>\n")
            handle.write("  </table>\n")
        handle.write("</lyriconcBackup>\n")
    return output_path


def read_backup(input_path: Path | str) -> dict[str, list[dict]]:
    root = ElementTree.parse(str(input_path)).getroot()
    if root.tag != "lyriconcBackup":
        raise XmlBackupError(f"Unexpected root element <{root.tag}>")
    tables: dict[str, list[dict]] = {}
    for table_element in root.findall("table"):
        name = table_element.get("name")
        if name not in TABLE_ORDER:
            raise XmlBackupError(f"Unknown table in backup file: {name}")
        rows = []
        for row_element in table_element.findall("row"):
            row = {
                field.tag: (None if field.get("null") == "true" else field.text or "")
                for field in row_element
            }
            rows.append(row)
        tables[name] = rows
    return tables


def restore_database_xml(conn: sqlite3.Connection, input_path: Path | str) -> dict:
    """Recreate the schema from DDL, then import every row from the XML file."""
    tables = read_backup(input_path)
    db.reset_database(conn)
    conn.execute("PRAGMA foreign_keys = ON")

    restored: dict[str, int] = {}
    try:
        for table in TABLE_ORDER:
            rows = tables.get(table, [])
            restored[table] = len(rows)
            for row in rows:
                columns = list(row)
                placeholders = ", ".join("?" for _ in columns)
                column_list = ", ".join(f'"{column}"' for column in columns)
                conn.execute(
                    f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})",
                    [row[column] for column in columns],
                )
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise XmlBackupError(
                f"Restore produced {len(violations)} foreign key violations"
            )
        conn.commit()
    except sqlite3.Error as error:
        conn.rollback()
        raise XmlBackupError(f"Restore failed: {error}") from error
    return restored


def verify_database_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return db.table_counts(conn, list(TABLE_ORDER))


def build_verification_report(
    before: dict[str, int], after: dict[str, int], backup_path: Path | str
) -> str:
    lines = [
        "LyriConc XML backup verification report",
        f"Backup file : {backup_path}",
        f"Generated at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        f"{'table':<22}{'before':>10}{'after':>10}{'status':>10}",
        "-" * 52,
    ]
    ok = True
    for table in TABLE_ORDER:
        before_count = before.get(table, 0)
        after_count = after.get(table, 0)
        matched = before_count == after_count
        ok = ok and matched
        lines.append(
            f"{table:<22}{before_count:>10}{after_count:>10}"
            f"{('OK' if matched else 'MISMATCH'):>10}"
        )
    lines += ["-" * 52, f"Result: {'PASSED' if ok else 'FAILED'}"]
    return "\n".join(lines) + "\n"
