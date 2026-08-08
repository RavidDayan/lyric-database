"""Filesystem locations used by the application.

Every path can be overridden with an environment variable so that tests and the
demo can run against throw-away directories.
"""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]

SCHEMA_PATH = PACKAGE_ROOT / "sql" / "schema.sql"


def _path_from_env(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser().resolve() if value else default


DATA_DIR = _path_from_env("LYRICONC_DATA_DIR", PROJECT_ROOT / "data")
CORPUS_DIR = _path_from_env("LYRICONC_CORPUS_DIR", DATA_DIR / "corpus")
DATABASE_PATH = _path_from_env("LYRICONC_DB", DATA_DIR / "lyriconc.db")
EXPORT_DIR = _path_from_env("LYRICONC_EXPORT_DIR", DATA_DIR / "exports")

CONTRIBUTOR_ROLES = ("PERFORMER", "LYRICIST", "COMPOSER")


def ensure_directories() -> None:
    for directory in (DATA_DIR, CORPUS_DIR, EXPORT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
