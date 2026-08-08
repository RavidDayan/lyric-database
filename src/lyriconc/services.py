"""Backend service layer.

The UI never writes SQL: every screen calls one of these methods. All SQL uses
bound parameters, so user input can never be concatenated into a statement.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from . import config, db, loader, xml_backup
from .parser import parse_file
from .tokenizer import normalize_token, tokenize, tokenize_with_spans

STATISTICS_LEVELS = ("line", "stanza", "document", "word_frequency")


class ServiceError(RuntimeError):
    pass


def _rows(cursor: sqlite3.Cursor) -> list[dict]:
    return [dict(row) for row in cursor.fetchall()]


class LyriConcService:
    """Single entry point used by the desktop application and by the tests."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else config.DATABASE_PATH
        self.conn = db.open_database(self.db_path)

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------
    # Function 1-2: loading documents and structured metadata
    # ------------------------------------------------------------------
    def reset_db(self) -> None:
        db.reset_database(self.conn)

    def load_folder(
        self, path: Path | str | None = None, metadata_defaults: dict | None = None
    ) -> dict:
        return loader.load_folder(self.conn, path, metadata_defaults)

    def load_file(
        self, path: Path | str, metadata_defaults: dict | None = None
    ) -> int:
        return loader.load_file(self.conn, path, metadata_defaults)

    def delete_document(self, document_id: int) -> None:
        loader.delete_document(self.conn, document_id)
        self.conn.commit()

    def list_documents(self) -> list[dict]:
        return _rows(
            self.conn.execute(
                """
                SELECT d.document_id,
                       d.title,
                       d.file_name,
                       d.file_path,
                       d.genre,
                       d.language,
                       d.release_year,
                       al.title AS album,
                       (SELECT group_concat(a.name, '; ')
                          FROM document_contributor dc
                          JOIN artist a ON a.artist_id = dc.artist_id
                         WHERE dc.document_id = d.document_id
                           AND dc.role = 'PERFORMER') AS performers,
                       (SELECT group_concat(a.name, '; ')
                          FROM document_contributor dc
                          JOIN artist a ON a.artist_id = dc.artist_id
                         WHERE dc.document_id = d.document_id
                           AND dc.role = 'LYRICIST') AS lyricists,
                       (SELECT group_concat(a.name, '; ')
                          FROM document_contributor dc
                          JOIN artist a ON a.artist_id = dc.artist_id
                         WHERE dc.document_id = d.document_id
                           AND dc.role = 'COMPOSER') AS composers,
                       (SELECT COUNT(*) FROM occurrence o
                         WHERE o.document_id = d.document_id) AS word_count
                  FROM document d
                  LEFT JOIN album al ON al.album_id = d.album_id
                 ORDER BY d.title
                """
            )
        )

    def get_document(self, document_id: int) -> dict | None:
        for row in self.list_documents():
            if row["document_id"] == document_id:
                return row
        return None

    def update_document_metadata(self, document_id: int, metadata: dict) -> None:
        row = self.conn.execute(
            "SELECT document_id FROM document WHERE document_id = ?", (document_id,)
        ).fetchone()
        if row is None:
            raise ServiceError(f"Unknown document {document_id}")

        album_id = loader.get_or_create_album(
            self.conn, metadata.get("album"), metadata.get("album_year")
        )
        assignments = {
            "title": metadata.get("title"),
            "genre": metadata.get("genre"),
            "language": metadata.get("language") or "English",
            "release_year": metadata.get("release_year"),
            "album_id": album_id,
        }
        if not (assignments["title"] or "").strip():
            raise ServiceError("Title must not be empty")
        self.conn.execute(
            "UPDATE document SET title = :title, genre = :genre, "
            "language = :language, release_year = :release_year, "
            "album_id = :album_id WHERE document_id = :document_id",
            {**assignments, "document_id": document_id},
        )
        loader.set_contributors(self.conn, document_id, metadata)
        self.conn.commit()

    def list_genres(self) -> list[str]:
        return [
            row["genre"]
            for row in self.conn.execute(
                "SELECT DISTINCT genre FROM document "
                "WHERE genre IS NOT NULL ORDER BY genre"
            )
        ]

    # ------------------------------------------------------------------
    # Function 3-4: retrieval by metadata or by word, and word lists
    # ------------------------------------------------------------------
    def search_documents(self, filters: dict | None = None) -> list[dict]:
        filters = filters or {}
        params = {
            "title": filters.get("title") or None,
            "genre": filters.get("genre") or None,
            "language": filters.get("language") or None,
            "artist": filters.get("artist") or None,
            "year_from": filters.get("year_from"),
            "year_to": filters.get("year_to"),
        }
        return _rows(
            self.conn.execute(
                """
                SELECT DISTINCT d.document_id, d.title, d.genre, d.language,
                       d.release_year, d.file_path
                  FROM document AS d
                  LEFT JOIN document_contributor AS dc
                         ON dc.document_id = d.document_id
                  LEFT JOIN artist AS a ON a.artist_id = dc.artist_id
                 WHERE (:title IS NULL OR d.title LIKE '%' || :title || '%')
                   AND (:genre IS NULL OR d.genre = :genre)
                   AND (:language IS NULL OR d.language = :language)
                   AND (:artist IS NULL OR a.name LIKE '%' || :artist || '%')
                   AND (:year_from IS NULL OR d.release_year >= :year_from)
                   AND (:year_to IS NULL OR d.release_year <= :year_to)
                 ORDER BY d.title
                """,
                params,
            )
        )

    def search_by_word(self, token: str) -> list[dict]:
        normalized = normalize_token(token)
        if not normalized:
            return []
        return _rows(
            self.conn.execute(
                """
                SELECT d.document_id, d.title, d.genre, d.release_year,
                       COUNT(*) AS occurrence_count
                  FROM word AS w
                  JOIN occurrence AS o ON o.word_id = w.word_id
                  JOIN document AS d ON d.document_id = o.document_id
                 WHERE w.normalized_token = :token
                 GROUP BY d.document_id, d.title, d.genre, d.release_year
                 ORDER BY occurrence_count DESC, d.title
                """,
                {"token": normalized},
            )
        )

    def get_word_list(self, document_ids: list[int] | None = None) -> list[dict]:
        if document_ids:
            placeholders = ", ".join("?" for _ in document_ids)
            sql = f"""
                SELECT w.word_id, w.normalized_token, w.char_count,
                       COUNT(*) AS frequency,
                       COUNT(DISTINCT o.document_id) AS document_count
                  FROM word AS w
                  JOIN occurrence AS o ON o.word_id = w.word_id
                 WHERE o.document_id IN ({placeholders})
                 GROUP BY w.word_id, w.normalized_token, w.char_count
                 ORDER BY frequency DESC, w.normalized_token
            """
            return _rows(self.conn.execute(sql, list(document_ids)))
        return _rows(
            self.conn.execute(
                """
                SELECT w.word_id, w.normalized_token, w.char_count,
                       COUNT(*) AS frequency,
                       COUNT(DISTINCT o.document_id) AS document_count
                  FROM word AS w
                  JOIN occurrence AS o ON o.word_id = w.word_id
                 GROUP BY w.word_id, w.normalized_token, w.char_count
                 ORDER BY frequency DESC, w.normalized_token
                """
            )
        )

    def get_occurrences(
        self, word_id: int, document_id: int | None = None
    ) -> list[dict]:
        return _rows(
            self.conn.execute(
                """
                SELECT o.occurrence_id, o.document_id, d.title,
                       w.normalized_token,
                       o.stanza_no, o.line_in_stanza, o.global_line_no,
                       o.word_offset + 1 AS word_position,
                       o.word_seq_in_doc
                  FROM occurrence AS o
                  JOIN document AS d ON d.document_id = o.document_id
                  JOIN word AS w ON w.word_id = o.word_id
                 WHERE o.word_id = :word_id
                   AND (:document_id IS NULL OR o.document_id = :document_id)
                 ORDER BY d.title, o.word_seq_in_doc
                """,
                {"word_id": word_id, "document_id": document_id},
            )
        )

    def get_word_id(self, token: str) -> int | None:
        normalized = normalize_token(token)
        if not normalized:
            return None
        row = self.conn.execute(
            "SELECT word_id FROM word WHERE normalized_token = ?", (normalized,)
        ).fetchone()
        return row["word_id"] if row else None

    # ------------------------------------------------------------------
    # Function 5: context of a word inside the original text
    # ------------------------------------------------------------------
    def get_context(
        self, occurrence_id: int, before: int = 4, after: int = 4
    ) -> dict:
        row = self.conn.execute(
            """
            SELECT o.occurrence_id, o.document_id, d.title, d.file_path,
                   w.normalized_token, o.stanza_no, o.line_in_stanza,
                   o.global_line_no, o.word_offset, o.word_seq_in_doc
              FROM occurrence AS o
              JOIN document AS d ON d.document_id = o.document_id
              JOIN word AS w ON w.word_id = o.word_id
             WHERE o.occurrence_id = ?
            """,
            (occurrence_id,),
        ).fetchone()
        if row is None:
            raise ServiceError(f"Unknown occurrence {occurrence_id}")

        path = Path(row["file_path"])
        if not path.is_file():
            raise ServiceError(f"Lyric file is missing: {path}")

        parsed = parse_file(path)
        line = parsed.find_line(row["stanza_no"], row["line_in_stanza"])
        if line is None:
            raise ServiceError(
                "The lyric file no longer matches the index. Reload the song."
            )

        physical = line.physical_line_no
        start = max(1, physical - before)
        end = min(len(parsed.physical_lines), physical + after)
        block = [
            {
                "physical_line_no": number,
                "text": parsed.physical_lines[number - 1],
                "is_match": number == physical,
            }
            for number in range(start, end + 1)
        ]

        spans = tokenize_with_spans(line.text)
        offset = row["word_offset"]
        char_start, char_end = (
            (spans[offset][1], spans[offset][2]) if offset < len(spans) else (0, 0)
        )
        return {
            "occurrence_id": row["occurrence_id"],
            "document_id": row["document_id"],
            "title": row["title"],
            "file_path": row["file_path"],
            "token": row["normalized_token"],
            "stanza_no": row["stanza_no"],
            "line_in_stanza": row["line_in_stanza"],
            "global_line_no": row["global_line_no"],
            "word_position": offset + 1,
            "word_seq_in_doc": row["word_seq_in_doc"],
            "match_physical_line_no": physical,
            "match_char_start": char_start,
            "match_char_end": char_end,
            "lines": block,
            "truncated_before": start > 1,
            "truncated_after": end < len(parsed.physical_lines),
        }

    def get_full_text(self, document_id: int) -> str:
        row = self.conn.execute(
            "SELECT file_path FROM document WHERE document_id = ?", (document_id,)
        ).fetchone()
        if row is None:
            raise ServiceError(f"Unknown document {document_id}")
        path = Path(row["file_path"])
        if not path.is_file():
            raise ServiceError(f"Lyric file is missing: {path}")
        return "\n".join(loader.read_document_lines(path))

    # ------------------------------------------------------------------
    # Function 6-7: the index with two position types, and reverse lookup
    # ------------------------------------------------------------------
    def get_word_index(
        self, document_id: int | None = None, group_id: int | None = None
    ) -> list[dict]:
        return _rows(
            self.conn.execute(
                """
                SELECT w.normalized_token, d.title, o.occurrence_id,
                       o.document_id,
                       o.stanza_no, o.line_in_stanza,
                       o.global_line_no, o.word_offset + 1 AS word_position,
                       o.word_seq_in_doc
                  FROM occurrence AS o
                  JOIN word AS w ON w.word_id = o.word_id
                  JOIN document AS d ON d.document_id = o.document_id
                 WHERE (:document_id IS NULL OR o.document_id = :document_id)
                   AND (:group_id IS NULL OR EXISTS (
                            SELECT 1 FROM word_group_member gm
                             WHERE gm.word_id = o.word_id
                               AND gm.group_id = :group_id))
                 ORDER BY w.normalized_token, d.title, o.word_seq_in_doc
                """,
                {"document_id": document_id, "group_id": group_id},
            )
        )

    def locate_word(
        self,
        document_id: int,
        stanza_no: int,
        line_in_stanza: int,
        word_offset: int,
    ) -> dict | None:
        """``word_offset`` is the 1-based value shown in the interface."""
        row = self.conn.execute(
            """
            SELECT w.normalized_token, o.occurrence_id, o.global_line_no,
                   o.word_seq_in_doc, d.title
              FROM occurrence AS o
              JOIN word AS w ON w.word_id = o.word_id
              JOIN document AS d ON d.document_id = o.document_id
             WHERE o.document_id = :document_id
               AND o.stanza_no = :stanza_no
               AND o.line_in_stanza = :line_in_stanza
               AND o.word_offset = :zero_based_word_offset
            """,
            {
                "document_id": document_id,
                "stanza_no": stanza_no,
                "line_in_stanza": line_in_stanza,
                "zero_based_word_offset": word_offset - 1,
            },
        ).fetchone()
        return dict(row) if row else None

    def locate_word_by_global_line(
        self, document_id: int, global_line_no: int, word_offset: int
    ) -> dict | None:
        row = self.conn.execute(
            """
            SELECT w.normalized_token, o.occurrence_id, o.stanza_no,
                   o.line_in_stanza, o.word_seq_in_doc, d.title
              FROM occurrence AS o
              JOIN word AS w ON w.word_id = o.word_id
              JOIN document AS d ON d.document_id = o.document_id
             WHERE o.document_id = ? AND o.global_line_no = ? AND o.word_offset = ?
            """,
            (document_id, global_line_no, word_offset - 1),
        ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Function 8: user-defined word groups
    # ------------------------------------------------------------------
    def create_group(self, name: str, description: str | None = None) -> int:
        name = (name or "").strip()
        if not name:
            raise ServiceError("Group name must not be empty")
        try:
            cursor = self.conn.execute(
                "INSERT INTO word_group (name, description) VALUES (?, ?)",
                (name, description),
            )
        except sqlite3.IntegrityError as error:
            raise ServiceError(f"Group '{name}' already exists") from error
        self.conn.commit()
        return int(cursor.lastrowid)

    def delete_group(self, group_id: int) -> None:
        self.conn.execute("DELETE FROM word_group WHERE group_id = ?", (group_id,))
        self.conn.commit()

    def list_groups(self) -> list[dict]:
        return _rows(
            self.conn.execute(
                """
                SELECT g.group_id, g.name, g.description,
                       (SELECT COUNT(*) FROM word_group_member gm
                         WHERE gm.group_id = g.group_id) AS word_count
                  FROM word_group AS g
                 ORDER BY g.name
                """
            )
        )

    def list_group_words(self, group_id: int) -> list[dict]:
        return _rows(
            self.conn.execute(
                """
                SELECT w.word_id, w.normalized_token,
                       (SELECT COUNT(*) FROM occurrence o
                         WHERE o.word_id = w.word_id) AS frequency
                  FROM word_group_member AS gm
                  JOIN word AS w ON w.word_id = gm.word_id
                 WHERE gm.group_id = ?
                 ORDER BY w.normalized_token
                """,
                (group_id,),
            )
        )

    def add_word_to_group(self, group_id: int, token: str) -> bool:
        """Add a word by typing it. Returns False when it is not in the corpus."""
        normalized = normalize_token(token)
        if not normalized:
            raise ServiceError(f"'{token}' is not a single valid word")
        cursor = self.conn.execute(
            """
            INSERT INTO word_group_member (group_id, word_id)
            SELECT :group_id, word_id FROM word WHERE normalized_token = :token
            ON CONFLICT (group_id, word_id) DO NOTHING
            """,
            {"group_id": group_id, "token": normalized},
        )
        self.conn.commit()
        if cursor.rowcount:
            return True
        exists = self.conn.execute(
            "SELECT 1 FROM word WHERE normalized_token = ?", (normalized,)
        ).fetchone()
        return bool(exists)

    def add_word_id_to_group(self, group_id: int, word_id: int) -> None:
        self.conn.execute(
            "INSERT INTO word_group_member (group_id, word_id) VALUES (?, ?) "
            "ON CONFLICT (group_id, word_id) DO NOTHING",
            (group_id, word_id),
        )
        self.conn.commit()

    def remove_word_from_group(self, group_id: int, token: str) -> None:
        normalized = normalize_token(token)
        self.conn.execute(
            "DELETE FROM word_group_member WHERE group_id = ? AND word_id IN "
            "(SELECT word_id FROM word WHERE normalized_token = ?)",
            (group_id, normalized),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Function 10: group-only index and its export
    # ------------------------------------------------------------------
    def get_group_index(
        self, group_id: int, document_id: int | None = None
    ) -> list[dict]:
        return _rows(
            self.conn.execute(
                """
                SELECT g.name AS group_name, w.normalized_token, d.title,
                       o.occurrence_id, o.document_id,
                       o.stanza_no, o.line_in_stanza, o.global_line_no,
                       o.word_offset + 1 AS word_position
                  FROM word_group AS g
                  JOIN word_group_member AS gm ON gm.group_id = g.group_id
                  JOIN word AS w ON w.word_id = gm.word_id
                  JOIN occurrence AS o ON o.word_id = w.word_id
                  JOIN document AS d ON d.document_id = o.document_id
                 WHERE g.group_id = :group_id
                   AND (:document_id IS NULL OR o.document_id = :document_id)
                 ORDER BY w.normalized_token, d.title, o.word_seq_in_doc
                """,
                {"group_id": group_id, "document_id": document_id},
            )
        )

    def export_group_index(
        self,
        group_id: int,
        output_path: Path | str,
        format: str = "txt",
        document_id: int | None = None,
    ) -> Path:
        rows = self.get_group_index(group_id, document_id)
        group = self.conn.execute(
            "SELECT name FROM word_group WHERE group_id = ?", (group_id,)
        ).fetchone()
        if group is None:
            raise ServiceError(f"Unknown group {group_id}")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        columns = [
            "normalized_token",
            "title",
            "stanza_no",
            "line_in_stanza",
            "global_line_no",
            "word_position",
        ]
        headers = [
            "word",
            "song",
            "stanza",
            "line in stanza",
            "global line",
            "word position",
        ]

        fmt = format.lower().lstrip(".")
        if fmt == "csv":
            with output_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                for row in rows:
                    writer.writerow([row[column] for column in columns])
        elif fmt == "txt":
            widths = [max(len(headers[i]), 18) for i in range(len(headers))]
            lines = [
                f"Index of word group: {group['name']}",
                f"Entries: {len(rows)}",
                "",
                "".join(h.ljust(w) for h, w in zip(headers, widths)),
                "-" * sum(widths),
            ]
            for row in rows:
                lines.append(
                    "".join(
                        str(row[column]).ljust(width)
                        for column, width in zip(columns, widths)
                    )
                )
            output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            raise ServiceError(f"Unsupported export format '{format}'")
        return output_path

    # ------------------------------------------------------------------
    # Function 9: stored linguistic expressions (phrases)
    # ------------------------------------------------------------------
    def create_phrase(self, name: str, tokens: list[str] | str) -> int:
        name = (name or "").strip()
        if not name:
            raise ServiceError("Phrase name must not be empty")
        token_list = tokenize(tokens) if isinstance(tokens, str) else list(tokens)
        token_list = [normalize_token(token) for token in token_list]
        token_list = [token for token in token_list if token]
        if not token_list:
            raise ServiceError("A phrase needs at least one word")

        missing = [
            token
            for token in token_list
            if self.conn.execute(
                "SELECT 1 FROM word WHERE normalized_token = ?", (token,)
            ).fetchone()
            is None
        ]
        if missing:
            raise ServiceError(
                "These words do not appear in the corpus: " + ", ".join(missing)
            )
        try:
            cursor = self.conn.execute(
                "INSERT INTO phrase (name) VALUES (?)", (name,)
            )
            phrase_id = int(cursor.lastrowid)
            for position, token in enumerate(token_list):
                self.conn.execute(
                    "INSERT INTO phrase_word (phrase_id, position, word_id) "
                    "SELECT ?, ?, word_id FROM word WHERE normalized_token = ?",
                    (phrase_id, position, token),
                )
        except sqlite3.IntegrityError as error:
            self.conn.rollback()
            raise ServiceError(f"Cannot store phrase '{name}': {error}") from error
        self.conn.commit()
        return phrase_id

    def delete_phrase(self, phrase_id: int) -> None:
        self.conn.execute("DELETE FROM phrase WHERE phrase_id = ?", (phrase_id,))
        self.conn.commit()

    def list_phrases(self) -> list[dict]:
        phrases = _rows(
            self.conn.execute(
                "SELECT phrase_id, name FROM phrase ORDER BY name"
            )
        )
        for phrase in phrases:
            phrase["tokens"] = " ".join(self.get_phrase_tokens(phrase["phrase_id"]))
        return phrases

    def get_phrase_tokens(self, phrase_id: int) -> list[str]:
        return [
            row["normalized_token"]
            for row in self.conn.execute(
                "SELECT w.normalized_token FROM phrase_word pw "
                "JOIN word w ON w.word_id = pw.word_id "
                "WHERE pw.phrase_id = ? ORDER BY pw.position",
                (phrase_id,),
            )
        ]

    def search_phrase(
        self, tokens: list[str] | str, document_id: int | None = None
    ) -> list[dict]:
        """Find an ordered word sequence; matches may span several lyric lines."""
        token_list = tokenize(tokens) if isinstance(tokens, str) else list(tokens)
        token_list = [normalize_token(token) for token in token_list]
        token_list = [token for token in token_list if token]
        if not token_list:
            return []

        word_ids: list[int] = []
        for token in token_list:
            row = self.conn.execute(
                "SELECT word_id FROM word WHERE normalized_token = ?", (token,)
            ).fetchone()
            if row is None:
                return []
            word_ids.append(row["word_id"])

        values = " UNION ALL ".join(
            "SELECT ? AS position, ? AS word_id" for _ in word_ids
        )
        params: list = []
        for position, word_id in enumerate(word_ids):
            params += [position, word_id]
        params += [document_id, document_id, len(word_ids)]

        candidates = _rows(
            self.conn.execute(
                f"""
                WITH pw(position, word_id) AS ({values})
                SELECT d.document_id, d.title,
                       o.word_seq_in_doc - pw.position AS start_word_seq,
                       MIN(o.global_line_no) AS first_line,
                       MAX(o.global_line_no) AS last_line
                  FROM pw
                  JOIN occurrence AS o ON o.word_id = pw.word_id
                  JOIN document AS d ON d.document_id = o.document_id
                 WHERE o.word_seq_in_doc >= pw.position
                   AND (? IS NULL OR o.document_id = ?)
                 GROUP BY d.document_id, d.title, start_word_seq
                HAVING COUNT(DISTINCT pw.position) = ?
                 ORDER BY d.title, start_word_seq
                """,
                params,
            )
        )

        results = []
        for candidate in candidates:
            row = self.conn.execute(
                "SELECT occurrence_id, stanza_no, line_in_stanza FROM occurrence "
                "WHERE document_id = ? AND word_seq_in_doc = ?",
                (candidate["document_id"], candidate["start_word_seq"]),
            ).fetchone()
            if row is None:
                continue
            results.append(
                {
                    **candidate,
                    "phrase": " ".join(token_list),
                    "length": len(token_list),
                    "occurrence_id": row["occurrence_id"],
                    "stanza_no": row["stanza_no"],
                    "line_in_stanza": row["line_in_stanza"],
                }
            )
        return results

    def search_phrase_by_id(self, phrase_id: int) -> list[dict]:
        return self.search_phrase(self.get_phrase_tokens(phrase_id))

    def search_marked_phrase(
        self, document_id: int, start_word_seq: int, length: int
    ) -> list[dict]:
        """Take a phrase marked inside the text and find its other appearances."""
        if length < 1:
            raise ServiceError("A marked phrase needs at least one word")
        tokens = [
            row["normalized_token"]
            for row in self.conn.execute(
                "SELECT w.normalized_token FROM occurrence o "
                "JOIN word w ON w.word_id = o.word_id "
                "WHERE o.document_id = ? AND o.word_seq_in_doc BETWEEN ? AND ? "
                "ORDER BY o.word_seq_in_doc",
                (document_id, start_word_seq, start_word_seq + length - 1),
            )
        ]
        if len(tokens) != length:
            raise ServiceError("The marked range is outside the song")
        return self.search_phrase(tokens)

    # ------------------------------------------------------------------
    # Function 11: statistics
    # ------------------------------------------------------------------
    def get_statistics(
        self, level: str, document_id: int | None = None
    ) -> list[dict]:
        if level not in STATISTICS_LEVELS:
            raise ServiceError(f"Unknown statistics level '{level}'")
        params = {"document_id": document_id}
        if level == "line":
            sql = """
                SELECT d.title, l.stanza_no, l.line_in_stanza, l.global_line_no,
                       l.char_count, l.word_count,
                       ROUND(CAST(l.char_count AS REAL) /
                             NULLIF(l.word_count, 0), 2) AS avg_word_chars
                  FROM lyric_line AS l
                  JOIN document AS d ON d.document_id = l.document_id
                 WHERE (:document_id IS NULL OR l.document_id = :document_id)
                 ORDER BY d.title, l.global_line_no
            """
        elif level == "stanza":
            sql = """
                SELECT d.title, s.stanza_no, s.line_count, s.word_count,
                       s.char_count,
                       ROUND(CAST(s.word_count AS REAL) /
                             NULLIF(s.line_count, 0), 2) AS avg_words_per_line
                  FROM stanza AS s
                  JOIN document AS d ON d.document_id = s.document_id
                 WHERE (:document_id IS NULL OR s.document_id = :document_id)
                 ORDER BY d.title, s.stanza_no
            """
        elif level == "document":
            sql = """
                SELECT d.document_id, d.title,
                       (SELECT COUNT(*) FROM stanza s
                         WHERE s.document_id = d.document_id) AS stanza_count,
                       (SELECT COUNT(*) FROM lyric_line l
                         WHERE l.document_id = d.document_id) AS line_count,
                       (SELECT COUNT(*) FROM occurrence o
                         WHERE o.document_id = d.document_id) AS word_count,
                       (SELECT COUNT(DISTINCT o.word_id) FROM occurrence o
                         WHERE o.document_id = d.document_id) AS distinct_words,
                       (SELECT COALESCE(SUM(l.char_count), 0) FROM lyric_line l
                         WHERE l.document_id = d.document_id) AS char_count
                  FROM document AS d
                 WHERE (:document_id IS NULL OR d.document_id = :document_id)
                 ORDER BY d.title
            """
        else:
            sql = """
                SELECT w.normalized_token, w.char_count,
                       COUNT(*) AS frequency,
                       COUNT(DISTINCT o.document_id) AS document_count
                  FROM word AS w
                  JOIN occurrence AS o ON o.word_id = w.word_id
                 WHERE (:document_id IS NULL OR o.document_id = :document_id)
                 GROUP BY w.word_id, w.normalized_token, w.char_count
                 ORDER BY frequency DESC, w.normalized_token
            """
        return _rows(self.conn.execute(sql, params))

    def export_rows(
        self, rows: list[dict], output_path: Path | str, title: str = "LyriConc report"
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not rows:
            output_path.write_text(f"{title}\n\n(no rows)\n", encoding="utf-8")
            return output_path
        columns = list(rows[0])
        if output_path.suffix.lower() == ".csv":
            with output_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns)
                writer.writeheader()
                writer.writerows(rows)
        else:
            widths = [
                max(len(column), *(len(str(row[column])) for row in rows)) + 2
                for column in columns
            ]
            lines = [title, "", "".join(c.ljust(w) for c, w in zip(columns, widths))]
            lines.append("-" * sum(widths))
            for row in rows:
                lines.append(
                    "".join(
                        str(row[column]).ljust(width)
                        for column, width in zip(columns, widths)
                    )
                )
            output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return output_path

    # ------------------------------------------------------------------
    # Additional topic: XML backup and restore
    # ------------------------------------------------------------------
    def export_database_xml(self, output_path: Path | str) -> Path:
        return xml_backup.export_database_xml(self.conn, output_path)

    def restore_database_xml(self, input_path: Path | str) -> dict:
        return xml_backup.restore_database_xml(self.conn, input_path)

    def verify_database_counts(self) -> dict[str, int]:
        return xml_backup.verify_database_counts(self.conn)

    def export_xml_verification_report(
        self,
        output_path: Path | str,
        before: dict[str, int],
        backup_path: Path | str,
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report = xml_backup.build_verification_report(
            before, self.verify_database_counts(), backup_path
        )
        output_path.write_text(report, encoding="utf-8")
        return output_path

    def run_xml_round_trip(
        self, backup_path: Path | str, report_path: Path | str | None = None
    ) -> dict:
        """Export, rebuild the database from DDL, restore and verify."""
        before = self.verify_database_counts()
        backup_path = Path(backup_path)
        self.export_database_xml(backup_path)
        self.restore_database_xml(backup_path)
        after = self.verify_database_counts()
        report = xml_backup.build_verification_report(before, after, backup_path)
        if report_path is not None:
            Path(report_path).parent.mkdir(parents=True, exist_ok=True)
            Path(report_path).write_text(report, encoding="utf-8")
        return {
            "before": before,
            "after": after,
            "passed": before == after,
            "report": report,
            "backup_path": str(backup_path),
        }
