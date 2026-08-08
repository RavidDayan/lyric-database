"""Parsing of a lyric ``.txt`` file into stanzas, lines and word occurrences.

File layout::

    Title: Amazing Grace
    Lyricist: John Newton
    Genre: Hymn

    Amazing grace how sweet the sound
    That saved a wretch like me

    I once was lost but now am found
    Was blind but now I see

The optional header block is a ``Key: value`` front matter terminated by a blank
line. It is only recognised when the first line uses a known key, so a lyric
line such as ``Chorus:`` is never mistaken for metadata. Multi-valued fields are
separated by semicolons.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .tokenizer import tokenize

FRONT_MATTER_KEYS = {
    "title": "title",
    "performer": "performers",
    "performers": "performers",
    "lyricist": "lyricists",
    "lyricists": "lyricists",
    "composer": "composers",
    "composers": "composers",
    "album": "album",
    "albumyear": "album_year",
    "album year": "album_year",
    "genre": "genre",
    "language": "language",
    "year": "release_year",
    "releaseyear": "release_year",
    "release year": "release_year",
    "source": "source",
}
LIST_FIELDS = {"performers", "lyricists", "composers"}
INT_FIELDS = {"album_year", "release_year"}

_HEADER_LINE = re.compile(r"^([A-Za-z][A-Za-z ]*):\s*(.*)$")


@dataclass(frozen=True)
class ParsedWord:
    token: str
    word_offset: int  # zero-based position inside the lyric line
    word_seq_in_doc: int  # zero-based position inside the whole song


@dataclass
class ParsedLine:
    stanza_no: int
    line_in_stanza: int
    global_line_no: int
    physical_line_no: int  # 1-based line number inside the file on disk
    text: str
    words: list[ParsedWord] = field(default_factory=list)

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def word_count(self) -> int:
        return len(self.words)


@dataclass
class ParsedStanza:
    stanza_no: int
    lines: list[ParsedLine] = field(default_factory=list)

    @property
    def line_count(self) -> int:
        return len(self.lines)

    @property
    def word_count(self) -> int:
        return sum(line.word_count for line in self.lines)

    @property
    def char_count(self) -> int:
        return sum(line.char_count for line in self.lines)


@dataclass
class ParsedDocument:
    metadata: dict
    stanzas: list[ParsedStanza]
    physical_lines: list[str]

    @property
    def lines(self) -> list[ParsedLine]:
        return [line for stanza in self.stanzas for line in stanza.lines]

    def find_line(self, stanza_no: int, line_in_stanza: int) -> ParsedLine | None:
        for stanza in self.stanzas:
            if stanza.stanza_no == stanza_no:
                for line in stanza.lines:
                    if line.line_in_stanza == line_in_stanza:
                        return line
        return None


def _coerce_value(field_name: str, raw: str):
    raw = raw.strip()
    if not raw:
        return None
    if field_name in LIST_FIELDS:
        return [part.strip() for part in raw.split(";") if part.strip()]
    if field_name in INT_FIELDS:
        match = re.search(r"\d{4}", raw)
        return int(match.group(0)) if match else None
    return raw


def split_front_matter(text: str) -> tuple[dict, int]:
    """Return ``(metadata, first_body_line_index)`` for the given file text."""
    lines = text.splitlines()
    if not lines:
        return {}, 0
    first = _HEADER_LINE.match(lines[0])
    if not first or first.group(1).strip().lower() not in FRONT_MATTER_KEYS:
        return {}, 0

    metadata: dict = {}
    index = 0
    for index, line in enumerate(lines):
        if not line.strip():
            index += 1
            break
        match = _HEADER_LINE.match(line)
        if not match:
            break
        key = FRONT_MATTER_KEYS.get(match.group(1).strip().lower())
        if key is None:
            break
        value = _coerce_value(key, match.group(2))
        if value is not None:
            metadata[key] = value
    else:
        index = len(lines)
    return metadata, index


def parse_text(text: str) -> ParsedDocument:
    metadata, body_start = split_front_matter(text)
    physical_lines = text.splitlines()

    stanzas: list[ParsedStanza] = []
    current: ParsedStanza | None = None
    global_line_no = 0
    word_seq_in_doc = 0

    for offset, raw_line in enumerate(physical_lines[body_start:]):
        physical_line_no = body_start + offset + 1
        if not raw_line.strip():
            current = None
            continue
        if current is None:
            current = ParsedStanza(stanza_no=len(stanzas) + 1)
            stanzas.append(current)
        global_line_no += 1
        line = ParsedLine(
            stanza_no=current.stanza_no,
            line_in_stanza=len(current.lines) + 1,
            global_line_no=global_line_no,
            physical_line_no=physical_line_no,
            text=raw_line.rstrip(),
        )
        for word_offset, token in enumerate(tokenize(raw_line)):
            line.words.append(ParsedWord(token, word_offset, word_seq_in_doc))
            word_seq_in_doc += 1
        current.lines.append(line)

    return ParsedDocument(metadata, stanzas, physical_lines)


def read_text(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8-sig")


def parse_file(path: Path | str) -> ParsedDocument:
    return parse_text(read_text(path))
