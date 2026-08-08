"""Loading lyric files into the relational index.

The raw lyric text is never inserted into a table: only the file path, the
structured metadata and the position index are stored.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import config
from .parser import ParsedDocument, parse_file, read_text


class LoaderError(RuntimeError):
    pass


def _get_or_create_artist(conn: sqlite3.Connection, name: str) -> int:
    name = name.strip()
    if not name:
        raise LoaderError("Artist name must not be empty")
    row = conn.execute(
        "SELECT artist_id FROM artist WHERE name = ?", (name,)
    ).fetchone()
    if row:
        return row["artist_id"]
    cursor = conn.execute("INSERT INTO artist (name) VALUES (?)", (name,))
    return int(cursor.lastrowid)


def get_or_create_album(
    conn: sqlite3.Connection, title: str | None, year: int | None
) -> int | None:
    if not title or not title.strip():
        return None
    title = title.strip()
    row = conn.execute(
        "SELECT album_id FROM album WHERE title = ? AND release_year IS ?",
        (title, year),
    ).fetchone()
    if row:
        return row["album_id"]
    cursor = conn.execute(
        "INSERT INTO album (title, release_year) VALUES (?, ?)", (title, year)
    )
    return int(cursor.lastrowid)


def _get_or_create_word(conn: sqlite3.Connection, token: str) -> int:
    row = conn.execute(
        "SELECT word_id FROM word WHERE normalized_token = ?", (token,)
    ).fetchone()
    if row:
        return row["word_id"]
    cursor = conn.execute(
        "INSERT INTO word (normalized_token, char_count) VALUES (?, ?)",
        (token, len(token)),
    )
    return int(cursor.lastrowid)


def set_contributors(
    conn: sqlite3.Connection, document_id: int, metadata: dict
) -> None:
    role_fields = {
        "PERFORMER": "performers",
        "LYRICIST": "lyricists",
        "COMPOSER": "composers",
    }
    for role, field_name in role_fields.items():
        if field_name not in metadata:
            continue
        conn.execute(
            "DELETE FROM document_contributor "
            "WHERE document_id = ? AND role = ?",
            (document_id, role),
        )
        for name in metadata.get(field_name) or []:
            artist_id = _get_or_create_artist(conn, name)
            conn.execute(
                "INSERT OR IGNORE INTO document_contributor "
                "(document_id, artist_id, role) VALUES (?, ?, ?)",
                (document_id, artist_id, role),
            )


def delete_document(conn: sqlite3.Connection, document_id: int) -> None:
    conn.execute("DELETE FROM document WHERE document_id = ?", (document_id,))


def _index_document(
    conn: sqlite3.Connection, document_id: int, parsed: ParsedDocument
) -> None:
    for stanza in parsed.stanzas:
        conn.execute(
            "INSERT INTO stanza "
            "(document_id, stanza_no, line_count, word_count, char_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                document_id,
                stanza.stanza_no,
                stanza.line_count,
                stanza.word_count,
                stanza.char_count,
            ),
        )
        for line in stanza.lines:
            conn.execute(
                "INSERT INTO lyric_line (document_id, stanza_no, line_in_stanza, "
                "global_line_no, char_count, word_count) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    document_id,
                    line.stanza_no,
                    line.line_in_stanza,
                    line.global_line_no,
                    line.char_count,
                    line.word_count,
                ),
            )
            for word in line.words:
                word_id = _get_or_create_word(conn, word.token)
                conn.execute(
                    "INSERT INTO occurrence (document_id, word_id, stanza_no, "
                    "line_in_stanza, global_line_no, word_offset, word_seq_in_doc) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        document_id,
                        word_id,
                        line.stanza_no,
                        line.line_in_stanza,
                        line.global_line_no,
                        word.word_offset,
                        word.word_seq_in_doc,
                    ),
                )


def load_file(
    conn: sqlite3.Connection,
    path: Path | str,
    metadata_defaults: dict | None = None,
) -> int:
    """Load one lyric file. Reloading the same path replaces its index rows."""
    path = Path(path).resolve()
    if not path.is_file():
        raise LoaderError(f"Not a file: {path}")

    parsed = parse_file(path)
    if not parsed.stanzas:
        raise LoaderError(f"No lyric lines found in {path.name}")

    metadata = dict(metadata_defaults or {})
    metadata.update(parsed.metadata)

    file_path = str(path)
    existing = conn.execute(
        "SELECT document_id FROM document WHERE file_path = ?", (file_path,)
    ).fetchone()
    if existing:
        delete_document(conn, existing["document_id"])

    album_id = get_or_create_album(
        conn, metadata.get("album"), metadata.get("album_year")
    )
    cursor = conn.execute(
        "INSERT INTO document (title, file_name, file_path, album_id, genre, "
        "language, release_year) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            (metadata.get("title") or path.stem.replace("_", " ")).strip(),
            path.name,
            file_path,
            album_id,
            metadata.get("genre"),
            metadata.get("language") or "English",
            metadata.get("release_year"),
        ),
    )
    document_id = int(cursor.lastrowid)
    set_contributors(conn, document_id, metadata)
    _index_document(conn, document_id, parsed)
    conn.commit()
    return document_id


def load_folder(
    conn: sqlite3.Connection,
    folder: Path | str | None = None,
    metadata_defaults: dict | None = None,
) -> dict:
    """Load every ``.txt`` file of a folder and report per-file results."""
    folder = Path(folder) if folder is not None else config.CORPUS_DIR
    if not folder.is_dir():
        raise LoaderError(f"Not a folder: {folder}")

    loaded: list[str] = []
    failed: list[tuple[str, str]] = []
    for path in sorted(folder.glob("*.txt")):
        try:
            load_file(conn, path, metadata_defaults)
            loaded.append(path.name)
        except (LoaderError, sqlite3.Error, UnicodeDecodeError) as error:
            conn.rollback()
            failed.append((path.name, str(error)))
    return {"folder": str(folder), "loaded": loaded, "failed": failed}


def read_document_lines(file_path: Path | str) -> list[str]:
    return read_text(file_path).splitlines()
