"""The single tokenizer used by the loader, search, phrases and statistics.

Frozen rules (Stage A contract):

* text is lower-cased;
* curly apostrophes are normalised to the ASCII apostrophe;
* an apostrophe *inside* a word is kept, so ``don't`` is one token;
* a leading or trailing apostrophe is dropped, so ``'tis`` becomes ``tis``;
* a hyphen splits a word, so ``well-known`` becomes two tokens;
* every other punctuation character is a separator;
* word offsets are stored zero-based and displayed one-based.
"""

from __future__ import annotations

import re

APOSTROPHES = "\u2019\u02bc\u2018\u0060\u00b4"
_APOSTROPHE_MAP = {ord(ch): "'" for ch in APOSTROPHES}

# [^\W_] is "word character except underscore", so accented letters survive.
TOKEN_PATTERN = re.compile(r"[^\W_]+(?:'[^\W_]+)*", re.UNICODE)


def normalize_text(text: str) -> str:
    return text.translate(_APOSTROPHE_MAP).lower()


def tokenize_with_spans(line: str) -> list[tuple[str, int, int]]:
    """Return ``(token, start, end)`` triples; spans index the original line."""
    normalized = normalize_text(line)
    return [
        (match.group(0), match.start(), match.end())
        for match in TOKEN_PATTERN.finditer(normalized)
    ]


def tokenize(line: str) -> list[str]:
    return [token for token, _, _ in tokenize_with_spans(line)]


def normalize_token(token: str) -> str:
    """Normalise a single user-typed search term, or return '' if unusable."""
    tokens = tokenize(token)
    return tokens[0] if len(tokens) == 1 else ""
